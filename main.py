import tornado.ioloop
import tornado.web
import os
import subprocess
import logging
import threading
import Queue
import json
import time
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPRequest
def getCompiler(arg):
    if arg=="cpp":
        return "tmp.cpp"
    else:
        return "tmp.py"
class taskObject(object):
    """docstring for task"""
    def __init__(self):
        self.timeLimit=""
        self.spaceLimit=""
        self.runId=""
        self.problemId=""
        self.compiler=""
        self.code=""
        self.cnt=0    

class judgeThread(threading.Thread): #The timer class is derived from the class threading.Thread  
    def __init__(self, num):  
        threading.Thread.__init__(self)  
        self.thread_num = num   
        self.thread_stop = False
        self.q = Queue.Queue(maxsize = 100)
    def run(self): #Overwrite run() method, put what you want the thread do here  
        while not self.thread_stop:  
            while not self.q.empty():
                task = self.q.get()
                print task 
                inputFileDir = "testcase/"+str(task.problemId)+"/test.in"
                outputFileDir = "testcase/"+str(task.problemId)+"/test.out"
                fetchCnt = 0
                while not os.path.exists(inputFileDir) or not os.path.exists(outputFileDir):
                    fetchCnt += 1
                    if fetchCnt>=20: 
                        break 
                    print "fetching testcase "+str(fetchCnt)
                    if not os.path.exists("testcase/"+str(task.problemId)):
                        os.mkdir("testcase/"+str(task.problemId))
                    def handle_in(response):
                        if response.error:
                            print "Error:", response.error
                        else:
                            file_object = open('testcase/'+task.problemId+'/test.in', 'w')
                            file_object.write(response.body)
                            file_object.close()

                    def handle_out(response):
                        if response.error:
                            print "Error:", response.error
                        else:
                            file_object = open('testcase/'+task.problemId+'/test.out', 'w')
                            file_object.write(response.body)
                            file_object.close()

                    http_client = AsyncHTTPClient()
                    http_client.fetch('http://192.168.58.190/ExamSystem/testdata/'+task.problemId+'/in',handle_in)
                    http_client.fetch('http://192.168.58.190/ExamSystem/testdata/'+task.problemId+'/out',handle_out)
                    time.sleep(0.3)
                if not os.path.exists(inputFileDir) or not os.path.exists(outputFileDir):
                    task.cnt+=1
                    if task.cnt<3:
                        self.q.put(task)
                    continue
                print "testcase ready"
                file_object = open('tmp/'+getCompiler(task.compiler), 'w')
                file_object.write(task.code)
                file_object.close()
                logging.info("GO!GO!GO!")
                commands = ["ljudge","--etc-dir","/home/yangz/.cache/ljudge", 
                    "--max-cpu-time", str(float(task.timeLimit) / 1000),
                    "--max-memory", task.spaceLimit,
                    "--user-code", 'tmp/'+getCompiler(task.compiler),
                    "--testcase",
                    "--input", inputFileDir,
                    "--output", outputFileDir]
                judgeResult =  subprocess.check_output(commands)
                print "transmit the result"
                def handle_request(response):
                    if response.error:
                        print "Error:", response.error
                    else:
                        print response.body
                data={}
                data["runId"]="123"
                data["result"]=judgeResult
                http_client = AsyncHTTPClient()
                AcOrWa = json.loads(judgeResult)
                #print AcOrWa
                AcFlag = True
                #print type(AcOrWa['compilation']['success'])
                if not AcOrWa['compilation']['success']:
                    AcFlag = False
                else:
                    AcOrWa = AcOrWa['testcases'][0]['result']
                    AcFlag = (AcOrWa == "ACCEPTED")
                print AcFlag
                http_request = HTTPRequest(
                    url='http://192.168.58.190/ExamSystem/result/'+task.runId+'/' + ('1' if AcFlag else '0'),
                    method='GET',
                    connect_timeout=10,
                    #body=json.dumps(data),
                )
                http_client.fetch(http_request,handle_request)
    def stop(self):  
        self.thread_stop = True
    def addTask(self,task):
        self.q.put(task)

class StopHandler(tornado.web.RequestHandler):
    def get(self):
        workThread.stop()
        self.write("stop")

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print "MainHandler Run"
        self.write("Hello, world")

class TestHandler(tornado.web.RequestHandler):
    def get(self):
        print "TestHandler Run"
        self.render("test.html")

class JudgeHandler(tornado.web.RequestHandler):
    def post(self):
        print "JudgeHandler Run"
        task = taskObject()
        task.timeLimit = self.get_argument("timeLimit");
        task.spaceLimit = self.get_argument("spaceLimit");
        task.problemId = self.get_argument("problemId");
        task.compiler = self.get_argument("compiler")
        task.runId = self.get_argument("runId");
        task.code = self.get_argument("code")
        print task.runId
        workThread.addTask(task)
        self.write("OK")

class ResultHandler(tornado.web.RequestHandler):
    def post(self):
        print "ResultHandler run"
        print self.request.body
        self.write("OK")        

class TestcaseHandler(tornado.web.RequestHandler):
    def get(self,arg):
        print "TestHandler Run"
        self.render("test/"+arg)

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/test",TestHandler),
    (r"/judge/",JudgeHandler),
    (r"/stop/",StopHandler),
    (r"/result/",ResultHandler),
    (r"/testcase/(.*)",TestcaseHandler),
])

workThread = judgeThread(1)
if __name__ == "__main__":
    workThread.setDaemon(True)
    workThread.start()
    #workThread.addTask(10)
    application.listen(8888)
    print "start at port 8888"
    tornado.ioloop.IOLoop.instance().start()
