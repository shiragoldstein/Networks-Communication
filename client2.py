import random
import socket
import string
import sys
import os
import time
from watchdog.observers import Observer
from watchdog.observers import polling
from watchdog.events import PatternMatchingEventHandler


try:
    IP = sys.argv[1]
    PORT = int(sys.argv[2])
    FOLDER_PATH = sys.argv[3]
    TIMEOUT = sys.argv[4]
except:
    print("error")
    sys.exit()

# for cutting the folder path from src path
path_length = len(FOLDER_PATH)

def send_folder_to_server(client_socket, folder_path):
    for path, dirs, files in os.walk(folder_path):

        for file in files:
            filename = os.path.join(path, file)
            relpath = os.path.relpath(filename, folder_path)
            filesize = os.path.getsize(filename)
            with open(filename, 'rb') as f:
                client_socket.sendall(relpath.encode() + b'\n')
                client_socket.sendall(str(filesize).encode() + b'\n')
                # Send the file in chunks so large files can be handled.
                while True:
                    data = f.read(1_000_000)
                    if not data:
                        break
                    client_socket.sendall(data)
        print('Done.')


def send_file_to_server(client_socket, src_path):
    with client_socket:
        filename = src_path
        # get file name from my_dir (file path)
        relpath = os.path.basename(filename)
        filesize = os.path.getsize(filename)

        print(f'Sending {relpath}')

        with open(filename, 'rb') as f:
            client_socket.sendall(relpath.encode() + b'\n')  # send file name + subdirectory and '\n'.
            client_socket.sendall(str(filesize).encode() + b'\n')  # send file size.

            # Send the file in chunks so large files can be handled.
            while True:
                data = f.read(1_000_000)
                if not data:
                    break
                client_socket.sendall(data)


def receive_folder_from_server(client_socket):
    with client_socket, client_socket.makefile('rb') as clientfile:
        while True:
            raw = clientfile.readline()
            # no more files, server closed connection.
            if not raw:
                break

            filename = raw.strip().decode()
            length = int(clientfile.readline())
            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

            path = os.path.join(FOLDER_PATH, filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # Read the data in chunks so it can handle large files.
            with open(path, 'wb') as f:
                while length:
                    chunk = min(length, 1_000_000)
                    data = clientfile.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    length -= len(data)
                # only runs if while doesn't break and length==0
                else:
                    print('Complete')
                    continue

            # socket was closed early.
            print('Incomplete')
            break


# send the path of the file/folder that was updated
def send_path(s, path):
    lengt = len(path)
    s.send(lengt.to_bytes(8, sys.byteorder))
    s.send(bytes(path, 'UTF-8'))


# get the path of the update
def get_path(client_socket):
    lengt = int.from_bytes(client_socket.recv(8), sys.byteorder)
    return str(client_socket.recv(lengt), 'utf-8')



def create(client_socket, final_path, folder_or_file):
    # folder_or_file = client_socket.recv(1).decode('utf-8')
    # server gets new folder
    if folder_or_file == "d":
        os.makedirs(final_path)
    # server gets new file
    if folder_or_file == "f":
        f = open(final_path, 'wb')
        # get the file in chunks so large files can be handled.
        while True:
            data = client_socket.recv(1024)
            while (data):
                f.write(data)
                #time.sleep(0.05)
                data = client_socket.recv(1024)
            f.close()
            break


# remove a folder and it's contents
def remove_folder(f_path):
    dirset = []
    # delete all files
    for path, dirs, files in os.walk(f_path):
        for file in files:
            file_name = os.path.join(path, file)
            os.remove(file_name)
    # delete all folders
    for subdirs, dirs, files in os.walk(f_path):
        for dir in dirs:
            dirname = os.path.join(subdirs, dir)
            dirset.append(dirname)
    dirset.reverse()
    for dir in dirset:
        os.rmdir(dir)
    os.rmdir(f_path)
    print("delete folder completed")


def delete(client_socket, final_path, folder_or_file):
    # folder_or_file = client_socket.recv(1).decode('utf-8')
    # server need to delete folder
    if folder_or_file == 'd':
        remove_folder(final_path)
    # server need to delete file
    if folder_or_file == 'f':
        if os.path.isfile(final_path):
            os.remove(final_path)
            print("delete file completed")
        else:
            print('The file doesnt exist')


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((IP, PORT))
# send first connection
s.send(b'0')
leng = len(sys.argv)
flag = 1
if len(sys.argv) == 6:
    ID = sys.argv[5]
    s.send(b'old')
    s.send(bytes(ID, 'utf-8'))
    # get the computer number of the user
    comp_num = int.from_bytes(s.recv(1), sys.byteorder)
    receive_folder_from_server(s)
else:
    s.send(b'new')
    ID = s.recv(128)
    ID = str(ID, 'utf-8')
    # get the computer number of the user
    comp_num = int.from_bytes(s.recv(1), sys.byteorder)
    send_folder_to_server(s, FOLDER_PATH)
    # get computer number of this computer
    # comp_num = int.from_bytes(s.recv(1), sys.byteorder)
s.close()

patterns = ["*"]
ignore_patterns = None
ignore_directories = False
case_sensitive = True
my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)


def on_created(event):
    if flag == 1:
        print(f"hey, {event.src_path} has been created!")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP, PORT))
        # send updates to server
        s.send(b'1')
        # save the new path of what the client created
        new_path = event.src_path[path_length: len(event.src_path)]
        # send the length and the name of the new path
        send_path(s, new_path)
        # send that something has created(folder/file)(index 1)
        s.send(bytes("c", 'utf-8'))
        # send the id of the current client
        s.send(bytes(ID, 'utf-8'))
        # send comp_num of the current computer
        s.send(comp_num.to_bytes(1, sys.byteorder))
        # if the event created a folder
        if event.is_directory:
            # send index that symbolize folder
            s.send(bytes("d", 'utf-8'))
        # if the event created a file
        else:
            # send index that symbolize file
            s.send(bytes("f", 'utf-8'))
            # send file to server
            f = open(event.src_path, 'rb')
            # Send the file in chunks so large files can be handled.
            data = f.read(1024)
            while (data):
                s.send(data)
                time.sleep(0.05)
                data = f.read(1024)
            f.close()
        s.close()


def on_deleted(event):
    if flag == 1:
        print(f"what the f**k! Someone deleted {event.src_path}!")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP, PORT))
        # send updates to server
        s.send(b'1')
        # save the new path of what the client created
        new_path = event.src_path[path_length: len(event.src_path)]
        # send the length and the name of the new path
        send_path(s, new_path)
        # send that something has deleted(folder/file)(index 1)
        s.send(bytes("d", 'utf-8'))
        # send the id of the current client
        s.send(bytes(ID, 'utf-8'))
        # send comp_num of the current computer
        s.send(comp_num.to_bytes(1, sys.byteorder))
        # if the event deleted a folder
        if event.is_directory:
            # send index that symbolize folder
            s.send(bytes("d", 'utf-8'))
        # if the event deleted a file
        else:
            # send index that symbolize file
            s.send(bytes("f", 'utf-8'))
        s.close()


# def on_modified(event):
#      print(f"hey buddy, {event.src_path} has been modified")


def on_moved(event):
    if flag == 1:
        print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")
        # the delete part
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP, PORT))
        # send updates to server
        s.send(b'1')
        # save the new path of what the client created
        new_path = event.dest_path[path_length: len(event.dest_path)]
        # send the length and the name of the new path
        send_path(s, new_path)
        # send that something has deleted(folder/file)(index 1)
        s.send(bytes("m", 'utf-8'))
        # send the id of the current client
        s.send(bytes(ID, 'utf-8'))
        # send comp_num of the current computer
        s.send(comp_num.to_bytes(1, sys.byteorder))
        # save the new path of what the client created
        src_path = event.src_path[path_length: len(event.src_path)]
        # send the length and the name of the new path
        # send_path(s, src_path)
        # if the event deleted a folder
        if event.is_directory:
            # send index that symbolize folder
            s.send(bytes("d", 'utf-8'))
            send_path(s, src_path)
            # send_folder_to_server(s, event.dest_path)
        # if the event deleted a file
        else:
            # send index that symbolize file
            s.send(bytes("f", 'utf-8'))
            send_path(s, src_path)
            # send file to server
            f = open(event.dest_path, 'rb')
            # Send the file in chunks so large files can be handled.
            data = f.read(1024)
            while (data):
                s.send(data)
                time.sleep(0.05)
                data = f.read(1024)
                if not data:
                    s.send(b'')
            f.close()
        s.close()


my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted
#my_event_handler.on_modified = on_modified
my_event_handler.on_moved = on_moved

path = FOLDER_PATH
go_recursively = True
my_observer = Observer()
# my_observer = polling.PollingObserver()
my_observer.schedule(my_event_handler, path, recursive=go_recursively)

my_observer.start()
try:
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((IP, PORT))
        # send me updates
        s.send(b'2')
        s.send(bytes(ID, 'utf-8'))
        s.send(comp_num.to_bytes(1, sys.byteorder))
        change = s.recv(1).decode('utf-8')
        while change != "x":
            flag = 0
            if change == "c":
                the_path = get_path(s)
                final_path = FOLDER_PATH + the_path
                folder_or_file = s.recv(1).decode('utf-8')
                create(s, final_path, folder_or_file)
            if change == "d":
                the_path = get_path(s)
                final_path = FOLDER_PATH + the_path
                folder_or_file = s.recv(1).decode('utf-8')
                delete(s, final_path, folder_or_file)
            flag = 1
            # get the new change
            change = s.recv(1).decode('utf-8')
        # if change == "x" - close socket
        s.close()

        # # send the id of the current client
        # s.send(bytes(ID, 'utf-8'))
        # # send comp_num of the current computer
        # s.send(comp_num.to_bytes(1, sys.byteorder))
        time.sleep(10)

except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()

# def send_msg(id, comp_num, type, location):
    