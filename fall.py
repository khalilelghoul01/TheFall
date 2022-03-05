from http.server import HTTPServer, BaseHTTPRequestHandler
import importlib
import json
import os
import sys
from traceback import print_tb
from turtle import back
from jinja2 import Template
from cryptography.fernet import Fernet
from pyfiglet import Figlet
from colorama import Fore, Back, Style
import signal

routesDir = "routes"
publicDir = "public"

RoutesLibDict = {}

class FallBase(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handleRouting(self)

    def do_POST(self):
        self.handleRouting(self)

    def do_PUT(self):
        self.handleRouting(self)

    def do_DELETE(self):
        self.handleRouting(self)

    def do_HEAD(self):
        self.handleRouting(self)

    def do_OPTIONS(self):
        self.handleRouting(self)
    
    def do_TRACE(self):
        self.handleRouting(self)
        
    def do_CONNECT(self):
        self.handleRouting(self)
        
    def do_PATCH(self):
        self.handleRouting(self)
        
    def import_module(self, name):
        module = importlib.import_module(name)
        return module

    def version_string(self):
        return "Fall/1.0"

    def log_message(self, format, *args):
        print(rgb_to_bg(0,0,0) + rgb_to_fg(0, 255, 225) +self.command + rgb_to_fg(8, 255, 905) + " - " + self.path + rgb_to_fg(252, 3, 94) + " - " + self.client_address[0]+Style.RESET_ALL)


    def parse_headers(self,headers):
        headers = headers.strip().split("\n")
        header_dict = {}
        for header in headers:
            key, value = header.split(": ")
            header_dict[key] = value
        return header_dict


    # def parse_cookies(self,cookies):
    #     cookies = cookies.strip().split("; ")
    #     cookie_dict = {}
    #     for cookie in cookies:
    #         key, value = cookie.split("=")
    #         cookie_dict[key] = value
    #     return cookie_dict

    def parse_cookies(self,cookies):
        cookies = cookies.strip().split("; ")
        cookie_dict = {}
        # handle cookies with = in value
        for cookie in cookies:
            kcookie = cookie.split("=")
            cookie_dict[kcookie[0]] = "=".join(kcookie[1:])
        return cookie_dict

    def handleRouting(self,fall):
        global RoutesLibDict
        path = self.path
        if not path.endswith("index"):
            path += "/"
        method = self.command
        if path.endswith("/"):
            path += "index"
        cookies = {}
        headers = self.parse_headers(str(self.headers))
        if("Cookie" in headers):
            cookies = self.parse_cookies(headers["Cookie"])
        service = ServeClient(cookies)
        if not os.path.exists(routesDir+path+".py"):
            if("." in path):
                if(os.path.exists(publicDir+path)):
                    service.serve_static(path)
                    serviceData = service.send()
                    self.send_Content(serviceData)
                    return
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"404 File not found")
                    return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"404 File not found")
                return
        if not path.endswith("/") and not path.endswith("index"):
            self.send_response(301)
            self.send_header("Location",path+"/")
        library = path.split("/")[-1]
        libraryFull = path.split("/")
        libraryFull = [string for string in libraryFull if string != '']
        libraryFull = routesDir+"."+".".join(libraryFull)
        if not libraryFull in RoutesLibDict :
            RoutesLibDict[libraryFull] = self.import_module(libraryFull)
            print(rgb_to_bg(0,0,0)+rgb_to_fg(255,255,0) + "Imported "+libraryFull+Style.RESET_ALL)
        serviceData = RoutesLibDict[libraryFull].handle(service,cookies,headers,method)
        self.send_Content(serviceData)

    def send_Content(self, serviceData):
        self.send_response(serviceData["status"])
        for key,value in serviceData["headers"].items():
            self.send_header(key,value)
        for key,value in serviceData["cookies"].items():
            self.send_header("Set-Cookie",key+"="+value)
        self.end_headers()
        self.wfile.write(serviceData["body"])


class ServeClient:
    def __init__(self,cookies):
        self.cookies = cookies
        self.headers = {}
        self.body = b''
        self.status = 200

    def add_cookie(self,key,value):
        self.cookies[key] = value
    
    def add_header(self,key,value):
        self.headers[key] = value

    def set_body(self,body):
        if isinstance(body,bytes):
            self.body = body
        else:
            self.body = bytes(body, "utf-8")
    
    def set_status(self,status):
        self.status = status

    def send(self):
        data = {}
        data["status"] = self.status
        data["body"] = self.body
        data["headers"] = self.headers
        data["cookies"] = self.cookies
        return data

    def serve_static(self,path):
        if path.startswith("/"):
            Dir = publicDir+path
        else:
            Dir = publicDir+"/"+path
        if(os.path.exists(Dir)):
            with open(Dir, "rb") as f:
                self.body = f.read()
                self.status = 200
                self.add_header("Content-Type", self.get_mime(path))
        else:
            self.status = 404

    def serve_template(self,path,data=[]):
        if path.startswith("/"):
            Dir = publicDir+path
        else:
            Dir = publicDir+"/"+path
        if(os.path.exists(Dir)):
            with open(Dir, "r") as f:
                template = Template(f.read())
                self.body = bytes(template.render(data), "utf-8")
                self.status = 200
                self.add_header("Content-Type", "text/html")
        else:
            self.status = 404

    def redirect(self,path):
        self.status = 301
        self.add_header("Location", path)

    def redirect_after(self,path,seconds):
        self.status = 200
        self.add_header("Refresh", str(seconds) + "; url=" + path)

    def downloadable(self,bool):
        self.status = 200
        if(bool):
            self.add_header("Content-Disposition", "attachment")
        else:
            self.add_header("Content-Disposition", "inline")

    def create_session(self,session):
        session = self.encrypt_message(session)
        self.add_cookie("fall_session",session)

    def get_session(self):
        if "fall_session" in self.cookies:
            session = self.decrypt_message(self.cookies["fall_session"])
            return session
        return None

    def check_session(self,session):
        if session == None:
            return False
        else:
            return True


    def get_mime(self,path):
        if(".html" in path):
            return "text/html"
        elif(".css" in path):
            return "text/css"
        elif(".js" in path):
            return "application/javascript"
        elif(".png" in path):
            return "image/png"
        elif(".jpeg" in path):
            return "image/jpeg"
        elif(".jpg" in path):
            return "image/jpeg"
        elif(".gif" in path):
            return "image/gif"
        elif(".svg" in path):
            return "image/svg+xml"
        elif(".ico" in path):
            return "image/x-icon"
        elif(".json" in path):
            return "application/json"
        else:
            return "text/plain"

    def store_key(self,key):
        with open("secret.key", "wb") as key_file:
            key_file.write(key)

    def create_key(self):
        if(os.path.exists("secret.key")):
            return
        key = Fernet.generate_key()
        self.store_key(key)

    def load_key(self):
        if(os.path.exists("secret.key")):
            with open("secret.key", "rb") as key_file:
                key = key_file.read()
        else:
            key = Fernet.generate_key()
            self.store_key(key)
        return key


    def encrypt_message(self,message):
        key = self.load_key()
        fernet = Fernet(key)
        encrypted_message = fernet.encrypt(message.encode())
        return encrypted_message.decode()

    def decrypt_message(self,encrypted_message):
        key = self.load_key()
        fernet = Fernet(key)
        decrypted_message = fernet.decrypt(encrypted_message.encode())
        return decrypted_message.decode()

    def serve_json(self,data):
        if isinstance(data,str):
            data = json.loads(data)
        self.set_body(json.dumps(data, indent=4))
        self.add_header("Content-Type", "application/json")

    

def rgb_to_fg(r,g,b):
    return "\033[38;2;{};{};{}m".format(r,g,b)

def rgb_to_bg(r,g,b):
    return "\033[48;2;{};{};{}m".format(r,g,b)

class Fall:
    def __init__(self, host="localhost", port=80):
        self.host = host
        self.port = port
        self.server = HTTPServer((host, port), FallBase)
        client = ServeClient({})
        client.create_key()

    def start(self):
        f = Figlet(font='slant')
        print(rgb_to_bg(0,0,0) + rgb_to_fg(66, 215, 245) +  f.renderText('The Fall') + Style.RESET_ALL)
        print(rgb_to_bg(0,0,0) + rgb_to_fg(225, 0, 255) + "Created by: @khalilelghoul01")
        print()
        print(rgb_to_bg(0,0,0) + rgb_to_fg(255, 178, 23) +"[+] Loading Routes" + Style.RESET_ALL)
        print()
        self.loadRoutes()
        print()
        print(rgb_to_bg(0,0,0) + rgb_to_fg(255, 255, 0)+"[+] Server is running on http://{}:{}".format(self.host, self.port)+Style.RESET_ALL)
        print(rgb_to_bg(0,0,0) + rgb_to_fg(255, 0, 0)+"Ctrl+C to quit"+Style.RESET_ALL)
        self.server.serve_forever()
        signal.signal(signal.SIGINT, self.handler)
    def stop(self):
        self.server.server_close()
    
    def handler(self,signum, frame):
        print("\n[+] Server is shutting down")
        self.stop()
        sys.exit(0)

    def loadRoutes(self,dir=routesDir):
        global RoutesLibDict
        # get all files in the routes directory
        routes = os.listdir(dir)
        # loop through all files
        for route in routes:
            # if the file is a directory, skip it
            if(os.path.isdir(routesDir+"/"+route)):
                self.loadRoutes(routesDir+"/"+route)
            # if the file is not a directory, load the route
            else:
                # get the route name
                routeName = route.split(".")[0]
                # get the route file
                fullroute = dir + "/" + routeName
                fullroute = fullroute.replace("routes/","/").replace("/index","/")
                if fullroute.endswith("/") and fullroute != "/":
                    fullroute  = fullroute[:-1]
                # add the route to the route list
                if "__pycache__" not in fullroute:
                    # load the route
                    if fullroute == "/":
                        fullroute = "index"
                    elif not fullroute.endswith("/"):
                        fullroute += "/index"
                    if(fullroute.startswith("/")):
                        fullroute = fullroute[1:]
                    libname = "routes."+fullroute.replace("/",".")
                    if libname in RoutesLibDict:
                        continue
                    # import the route importlib.import_module(libname)
                    route = importlib.import_module(libname)
                    # add the route to the route list
                    print(rgb_to_bg(0,0,0) + rgb_to_fg(255, 178, 23) + "Loading route: "+fullroute+Style.RESET_ALL)
    
                    RoutesLibDict[libname] = route



def handler(signum, frame):
    print( rgb_to_bg(0,0,0) + rgb_to_fg(255, 0, 0) + "[+] Server is shutting down"+Style.RESET_ALL)
    sys.exit(0)
signal.signal(signal.SIGINT, handler)

if __name__ == "__main__":
    fall = Fall()
    fall.start()


