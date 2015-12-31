from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import urlparse
import httplib
import logging

HOST_NAME = ''
PORT_NUMBER = 4570


class Proxy_Server(BaseHTTPRequestHandler):
    def do_GET(self):
        logging.info(self.path)

        #  getting data from Alice
        request_method = self.command
        request_url = self.path
        _request_len = self.headers.getheader('content-length')
        request_body = self.rfile.read(0 if _request_len is None else int(_request_len))
        request_headers = self.headers.dict  # as dictionary

        #  connecting to Bob
        parsed_url = urlparse(request_url)
        fact = httplib.HTTPSConnection if parsed_url.scheme == 'https' else httplib.HTTPConnection
        conn = fact(parsed_url.netloc)
        conn.request(request_method, parsed_url.path + '?' + parsed_url.query, headers=request_headers,
                     body=request_body)

        #  geting response from Bob
        resp = conn.getresponse()
        respone_data = ''
        _buff_size = 0
        while True:
            _buff_line = resp.read(1)
            if _buff_line == '':
                break
            _buff_size = _buff_size + 1
            respone_data += _buff_line
        foo = str(_buff_size)
        respone_headers = dict(resp.msg.dict)  # wywalic transfer encoding i dac content len, co sie dzieje z kodowaniem?
        for key in respone_headers:
            if key.lower() == 'Transfer-Encoding'.lower():
                respone_headers.pop(key, None)
                break
        for key in respone_headers:
            if key.lower() == 'Connection'.lower():
                respone_headers.pop(key, None)
                break
        respone_headers['Connection'] = 'close'

        found = False
        for key in respone_headers:
            if key.lower() == 'Content-Length'.lower():
                respone_headers.pop(key, None)
                break
        if not found:
            respone_headers['Content-Length'] = str(len(respone_data))





        # replying to Alice
        self.send_response(resp.status)
        for key in respone_headers:
            self.send_header(key, respone_headers[key])
        # self.send_header("Content-type", "text/html; charset=utf-8") #  example header
        self.end_headers()
        self.wfile.write(respone_data)

    do_POST = do_GET


if __name__ == "__main__":
    # URL = 'http://www.tcs.uj.edu.pl/wydarzenia'
    # URL = 'http://www.portal.uj.edu.pl/documents/35126571/ab59a209-60eb-451e-9489-0ab3c7facb00'
    # url = urlparse(URL)
    # print url
    # fact = httplib.HTTPSConnection if url.scheme == 'https' else httplib.HTTPConnection
    # conn = fact(url.netloc)
    # conn.request("GET", url.path + '?' + url.query)
    # resp = conn.getresponse()
    # print resp.status, resp.reason
    # data = resp.read()
    # pass

    logging.basicConfig(filename='log.txt', level=logging.INFO)
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), Proxy_Server)
    while 1:
        try:
            httpd.serve_forever()
        except:
            pass

