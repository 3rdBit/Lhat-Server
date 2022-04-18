import settings
import socket
import threading
import queue
import json  # json.dumps(some)打包   json.loads(some)解包
import os
import os.path
import sys
from server_operations import *

'''
变量备忘录
user_connections: 
    第一层索引：列表中的每一个元素都是列表，列表中存储着每个在线用户的信息
    第二层索引：
        0: 用户名
        1: 用户名的tcp连接实例
message: 
    0: IP地址和端口
    1: 打包消息内容
online_users: 在线用户列表
'''

ip = settings.ip_address
port = settings.network_port

messages = queue.Queue()
user_connections = []  # 0:userName 1:connection
lock = threading.Lock()


def OnOnline():
    online = []
    for new_index in range(len(user_connections)):
        online.append(user_connections[new_index][0])
    online = json.dumps(online)
    return online


class Server(threading.Thread):
    global user_connections, lock

    def __init__(self):  # 构造函数
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        os.chdir(sys.path[0])
        print('Running server on ' + ip + ':' + str(port))
        print('  To change the ip address, \n  please visit settings.py')
        print('Waiting for connection...')

    # 接受来自客户端的用户名，如果用户名为空，使用用户的IP与端口作为用户名。如果用户名出现重复，则在出现的用户名依此加上后缀“2”、“3”、“4”……
    def receive(self, conn, address):  # 接收消息
        user = conn.recv(1024)  # 用户名称
        user = user.decode('utf-8')
        if user == '用户名不存在':
            user = address[0] + ':' + str(address[1])
        tag = 1
        temp = user
        for i in range(len(user_connections)):  # 检验重名，则在重名用户后加数字
            if user_connections[i][0] == user:
                tag = tag + 1
                user = temp + str(tag)
        user_connections.append((user, conn))
        online_users = OnOnline()
        self.Load(online_users, address, online_users.encode('utf-8'))
        # 在获取用户名后便会不断地接受用户端发来的消息（即聊天内容），结束后关闭连接。
        try:
            while True:
                message = conn.recv(1024)  # 接收用户发来的消息
                message_string = message.decode('utf-8')
                self.Load(message_string, address, message)
        # 如果用户断开连接，将该用户从用户列表中删除，然后更新用户列表。
        except Exception as e:
            print(e)
            j = 0  # 用户断开连接
            for man in user_connections:
                if man[0] == user:
                    user_connections.pop(j)  # 服务器段删除退出的用户
                    break
                j = j + 1

            online_users = OnOnline()
            self.Load(online_users, address)
            conn.close()

    # 将地址与数据（需发送给客户端）存入messages队列。
    @staticmethod
    def Load(data, address, raw_data=b''):
        lock.acquire()
        try:
            messages.put((address, data, raw_data))
        finally:
            lock.release()

            # 服务端在接受到数据后，会对其进行一些处理然后发送给客户端，如下图，对于聊天内容，服务端直接发送给客户端，而对于用户列表，便由json.dumps处理后发送。

    def sendData(self):  # 发送数据
        while True:
            if not messages.empty():
                message = messages.get()
                message_json = unpack(message[1])
                if message_json[0] == 'USER_NAME':
                    for i in range(len(user_connections)):
                        try:
                            user_connections[i][1].send(pack(message_json[1], None,
                                                             'Lhat! Chatting Room', 'USER_MANIFEST'))
                        except Exception as e:
                            print(e)
                else:
                    for i in range(len(user_connections)):
                        user_connections[i][1].send(message[2])
                        print(message[1])
                        print('\n')

    def run(self):
        self.s.bind((ip, port))
        self.s.listen(10)
        q = threading.Thread(target=self.sendData)
        q.start()
        while True:
            conn, address = self.s.accept()
            print('Connection established: ' + address[0] + ':' + str(address[1]))
            t = threading.Thread(target=self.receive, args=(conn, address))
            t.start()


if __name__ == '__main__':
    server = Server()
    server.start()
