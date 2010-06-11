import httplib2
import urllib
import rfc822
import datetime
import hashlib
import base64
import sys
from xml.etree  import ElementTree as etree
from xml.dom    import minidom

DEBUG = False

class API(object):
  accessKey     = None
  secretKey     = None
  host          = None
  base          = None
  
  def __init__(self, username, password, base='http://localhost/cerb5/index.php/rest'):
    self.accessKey  = username
    self.secretKey  = password
    self.base       = base
    self.ext        = 'json'
    
  def get(self, url):
    return self.__connect('GET', url)
  
  def put(self, url, payload):
    return self.__connect('PUT', url, payload)
  
  def post(self, url, payload):
    return self.__connect('POST', url, payload)
  
  def delete(self, url):
    return self.__connect('DELETE', url)
  
  def listTickets(self):
    return self.__getList('tickets/list')
  
  def listOrgs(self):
    return self.__getList('orgs/list')
  
  def listAddresses(self):
    return self.__getList('addresses/list')
  
  def listMessages(self, ticket):
    return self.__getList('messages/list?ticket_id=%s' % ticket)
  
  def listComments(self, ticket):
    return self.__getList('comments/list?ticket_id=%s' % ticket)
  
  def listTasks(self):
    return self.__getList('tasks/list')
  
  def getTicket(self, ticket):
    return self.__genDict(
            etree.fromstring(
              self.get('tickets/%s' % str(ticket))))
  
  def getComment(self, comment):
    return self.__genDict(
            etree.fromstring(
              self.get('comments/%s' % str(comment))))
  
  def getNote(self, note):
    return self.__genDict(
            etree.fromstring(
              self.get('notes/%s' % str(note))))
  
  def createNote(self, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('notes/create', 
                self.__genPayload('note', **args))))
  
  def createAddresses(self, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('addresses/create', 
                self.__genPayload('address', **args))))
  
  def createComment(self, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('comments/create', 
                self.__genPayload('comment', **args))))
  
  def createOrg(self, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('orgs/create', 
                self.__genPayload('org', **args))))
  
  def updateTicket(self, ticket, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('tickets/%s' % ticket, 
                self.__genPayload('ticket', **args))))
  
  def updateAddress(self, address, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('addresses/%s' % address, 
                self.__genPayload('address', **args))))
  
  def updateOrg(self, org, **args):
    return self.__genDict(
            etree.fromstring(
              self.post('orgs/%s' % org, 
                self.__genPayload('org', **args))))

  def deleteComment(self, comment):
    return self.delete('comments/%s' % str(comment))
  
  def deleteNote(self, note):
    return self.delete('notes/%s' % str(note))
  
  def find(self, dataType, **args):
    params = []
    for param in args:
      params.append('<%s oper="%s" value="%s"/>' % (param, 
                                                    params[param]['oper'],
                                                    params[param]['value']))
    payload = '''
    <search>
      <params>
        %s
      </params>
    </search>
    ''' % '\n    '.join(params)
    return self.__genDict(
            etree.fromstring(
              self.post('%s/search' % dataType, payload)))
  
  
  def listArticles(self, sort=None, limit=None, root=None):
    search = []
    searchCriteria = ''
    if sort is not None:
      search.append('sort=%s' & str(sort))
    if limit is not None:
      search.append('limit=%s' & str(limit))
    if root is not None:
      search.append('root=%s' & str(root))
    if len(search) > 0:
      searchCriteria = '?' + '&'.join(search)
    return self.__getList('articles/list%s' % searchCriteria)
  
  def __genPayload(self, tag, **elements):
    lines = []
    for element in elements:
      lines.append('<%s>%s</%s>' % (element, elements[element], element))
    return '<%s>\n  %s\n</%s>' % (tag, '\n  '.join(lines), tag)
  
  def __getRFC822Date(self):
    return rfc822.formatdate(
            rfc822.mktime_tz(
              rfc822.parsedate_tz(
                datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S'))))
  
  def __genDict(self, tree):
    ret_dict = {}
    for item in tree.getchildren():
      ret_dict[item.tag] = item.text
    return ret_dict
  
  def __getList(self, url):
    tree = etree.fromstring(self.get(url))
    itemList = []
    for item in tree.getchildren():
      itemList.append(self.__genDict(item))
    return itemList
  
  def __connect(self, verb, url, payload={}):
    headers   = {
                'Date': self.__getRFC822Date(),
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
    }
    splitUrl  = urllib.splitquery(url)
    path      = splitUrl[0]
    if splitUrl[1] is not None:
      query   = splitUrl[1]
      fullUrl = '%s/%s.%s?%s' % (self.base, path, self.ext, query)
    else:
      query   = ''
      fullUrl = '%s/%s.%s' % (self.base, path, self.ext)
    verb      = verb.upper()
    http      = httplib2.Http()

    # Building the Authentication
    md5       = hashlib.md5()
    md5.update(self.secretKey)
    secret    = md5.hexdigest()
    fpath     = urllib.splitquery('/' + '/'.join(fullUrl.split('/')[3:]))[0]
    payload   = urllib.urlencode(payload)
    signMe    = '%s\n%s\n%s\n%s\n%s\n%s\n' % (verb,
                                              headers['Date'],
                                              fpath,
                                              query,
                                              payload,
                                              secret
                                             )
    md5      = hashlib.md5()
    md5.update(signMe)
    headers['Cerb5-Auth']  = '%s:%s' % (self.accessKey, md5.hexdigest())
    
    # Now we perform the request
    if verb == 'PUT' or verb == 'POST':
      headers['Content-Length'] = str(len(str(payload)))
      response, data = http.request(fullUrl, 
                                    verb, 
                                    headers=headers,
                                    body=payload)    
    else:
      response, data = http.request(fullUrl, 
                                    verb, 
                                    headers=headers)
    
    if DEBUG:
      print '--- REQUEST ---'
      print verb, fullUrl
      print 'HEADERS:'
      for header in headers:
        print '%20s : %s' % (header, headers[header])
      print 'PAYLOAD:\n%s' % payload
      print '\n--- RESPONSE ---'
      print 'HEADERS:'
      for header in response:
        print '%20s : %s' % (header, response[header])
      print 'PAYLOAD:'
      print data
    return data


def runTests(api):
  
  # Setting Debug for the tests
  DEBUG = True
  
  # Basic Get Test
  tickets       = api.listTickets()
  for ticket in tickets:
    print '     Ticket ID : %s' % ticket['id']
    print 'Ticket Subject : %s' % ticket['subject']
    print 'Message Count  : %s\n' % len(api.listMessages(ticket['id']))
  
  # Getting Messages for a ticket.
  messages = api.listMessages(99)
  for message in messages:
    print '--- Message ---'
    for item in message:
      print '%20s : %s' % (item, message[item])
  
  # Testing creation functionality
  response = api.createNote(message_id=99, 
                            worker_id=622, 
                            content='Test Comment')
  
  note = api.getNote(1)
  print '--- Note ---'
  for item in note:
    print '%20s : %s' % (item, note[item])
  
  print api.deleteNote(1)
  
def basic_auth_test():
  api = API('steve@localhost','linuxx','http://192.168.101.142/helpdesk/index.php/rest')
  print api.get('tickets/list')


if __name__ == '__main__':
  if len(sys.argv) >= 4:
    access_key    = sys.argv[1]
    secret_key    = sys.argv[2]
    base          = sys.argv[3]
    api           = API(access_key, secret_key, base)
    runTests(api)
  else:
    print 'Exmaple usage is as follows:'
    print '%s ACCESS_KEY SECRET_KEY BASE_URL' % sys.argv[0]
