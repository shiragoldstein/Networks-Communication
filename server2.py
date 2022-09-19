import random
import socket
import os
import string
import sys
import time

CHUNKSIZE = 1_000_000

try:
    PORT = int(sys.argv[1])
except:
    print("error")
    sys.exit()


def receive_folder_from_client(client_socket, id_data):
    with client_socket, client_socket.makefile('rb') as clientfile:
        while True:
            raw = clientfile.readline()
            # no more files, server closed connection.
            if not raw:
                break

            filename = raw.strip().decode()
            length = int(clientfile.readline())
            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

            path = os.path.join(id_data, filename)
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


# get one file from client
def receive_file_from_client(client_socket, id_data):
    line = " "
    while True:
        if not line:
            break  # no more files, client closed connection.
        line = client_socket.readline()
        filename = line.strip().decode()
        length = int(client_socket.readline())
        print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

        file_path = os.path.join('AllClients', str(id_data))
        file_path = os.path.join(file_path, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Read the data in chunks so it can handle large files.
        with open(file_path, 'wb') as f:
            while length:
                chunk = min(length, CHUNKSIZE)
                data = client_socket.read(chunk)
                if not data:
                    break
                f.write(data)
                length -= len(data)
            else:  # only runs if while doesn't break and length==0
                print('Complete')
                continue

        # socket was closed early.
        print('Incomplete')
        break
    client_socket.close()


def send_folder_to_client(s, id_data):
     for path, dirs, files in os.walk(id_data):
         for file in files:
             filename = os.path.join(path, file)
             relpath = os.path.relpath(filename, id_data)
             filesize = os.path.getsize(filename)
             with open(filename, 'rb') as f:
                 s.sendall(relpath.encode() + b'\n')
                 s.sendall(str(filesize).encode() + b'\n')
                 # Send the file in chunks so large files can be handled.
                 while True:
                     data = f.read(1_000_000)
                     if not data:
                         break
                     s.sendall(data)
         print('Done.')


def create(client_socket, id_data, final_path, folder_or_file):
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



def delete(client_socket, id_data, final_path, folder_or_file):
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


# get the path of the update
def get_path(client_socket):
    lengt = int.from_bytes(client_socket.recv(8), sys.byteorder)
    return str(client_socket.recv(lengt), 'utf-8')


def send_path(s, path):
    lengt = len(path)
    s.send(lengt.to_bytes(8, sys.byteorder))
    s.send(bytes(path, 'UTF-8'))


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('', PORT))
server.listen(5)
comp_num = 1
dictionary_id = {}


def update_clients(id_data, dictionary_id, change, path, folder_or_file, computer_number):
    change_folder_or_file = change + folder_or_file
    for computer in dictionary_id[id_data].keys():
        if computer != computer_number:
            dictionary_id[id_data][computer].append(change_folder_or_file + path)


# first connection with the server
while True:
    client_socket, client_address = server.accept()
    first_or_update = client_socket.recv(1).decode('utf-8')
    # first connection
    if first_or_update == "0":
        # create the computer dictionary
        dictionary_compnum = {}
        changes_list = []
        new_or_old = client_socket.recv(3)
        new_or_old = new_or_old.decode('utf-8')
        # in case of new id
        if new_or_old == "new":
            id_data = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=128))
            client_socket.send(bytes(id_data, 'utf-8'))
            os.makedirs(str(id_data), exist_ok=True)
            client_socket.send(comp_num.to_bytes(1, sys.byteorder))
            receive_folder_from_client(client_socket, id_data)

            dictionary_compnum[comp_num] = changes_list
            dictionary_id[id_data] = dictionary_compnum
            comp_num += 1
        # in case of old id
        else:
            id_data = client_socket.recv(128).decode('utf-8')     # get the id from client
            # send to the user his computer number
            client_socket.send(comp_num.to_bytes(1, sys.byteorder))
            send_folder_to_client(client_socket, id_data)

            dictionary_id[id_data][comp_num] = changes_list
            comp_num += 1


    # if we want to get updates
    if first_or_update == "1":
        # get the new path
        src_path = get_path(client_socket)
        # get the type of the update
        type_update = client_socket.recv(1).decode('utf-8')
        # gert the id of the client
        id_data = client_socket.recv(128).decode('utf-8')
        # make the final path
        final_path = id_data + src_path
        # get the comp num
        computer_number = int.from_bytes(client_socket.recv(1), sys.byteorder)
        # if the client created new folder/file
        folder_or_file = client_socket.recv(1).decode('utf-8')
        if type_update == "c":
            # the client created a folder or file
            create(client_socket, id_data, final_path, folder_or_file)
            update_clients(id_data, dictionary_id, "c", src_path, folder_or_file, computer_number)
        # if the client deleted new folder/file
        if type_update == "d":
            delete(client_socket, id_data, final_path, folder_or_file)
            update_clients(id_data, dictionary_id, "d", src_path, folder_or_file, computer_number)
        # if the client moved folder/file
        if type_update == "m":
            # create the folder/file
            dst_path = get_path(client_socket)
            src_path_move = id_data + dst_path
            # create the folder in the new location
            #dir_or_file = client_socket.recv(1).decode('utf-8')
            # if its folder
            if folder_or_file == "d":
                # get the folder to new location
                # receive_folder_from_client(client_socket, final_path)
                os.makedirs(final_path)
            # if its file
            else:
                f = open(final_path, 'wb')
                # get the file in chunks so large files can be handled.
                while True:
                    data = client_socket.recv(1024)
                    while (data):
                        f.write(data)
                        data = client_socket.recv(1024)
                    f.close()
                    break
            # # remove the folder/file
            # dst_path = get_path(client_socket)
            # final_dst_path = id_data + dst_path
            # delete(client_socket, id_data, final_path)
            if folder_or_file == 'd':
                if os.path.isdir(src_path_move):
                    remove_folder(src_path_move)
                else:
                    print('The folder doesnt exist')
            # server need to delete file
            if folder_or_file == 'f':
                if os.path.isfile(src_path_move):
                    os.remove(src_path_move)
                    print("delete file completed")
                else:
                    print('The file doesnt exist')

            update_clients(id_data, dictionary_id, "c", dst_path, folder_or_file, computer_number)
            update_clients(id_data, dictionary_id, "d", src_path_move, folder_or_file, computer_number)


    # if we want to update the client
    if first_or_update == "2":
        # get the id of the client
        id_data = client_socket.recv(128).decode('utf-8')
        # get the comp num
        computer_number = int.from_bytes(client_socket.recv(1), sys.byteorder)

        for change in dictionary_id[id_data][computer_number]:
            # create
            if change[0] == "c":
                client_socket.send(bytes("c", 'utf-8'))
                # save the new path of what the client created
                new_path = change[2: len(change)]
                # send the length and the name of the new path
                send_path(client_socket, new_path)
                if change[1] == "d":
                    # send index that symbolize folder
                    client_socket.send(bytes("d", 'utf-8'))
                # if the event created a file
                else:
                    # send index that symbolize file
                    client_socket.send(bytes("f", 'utf-8'))
                    # send file to server
                    f = open(id_data+new_path, 'rb')
                    # Send the file in chunks so large files can be handled.
                    data = f.read(1024)
                    while (data):
                        client_socket.send(data)
                        time.sleep(0.05)
                        data = f.read(1024)
                    f.close()

            # delete
            if change[0] == "d":
                client_socket.send(bytes("d", 'utf-8'))
                # save the new path of what the client created
                new_path = change[2: len(change)]
                # send the length and the name of the new path
                send_path(client_socket, new_path)
                if change[1] == "d":
                    # send index that symbolize folder
                    client_socket.send(bytes("d", 'utf-8'))
                else:
                    # send index that symbolize file
                    client_socket.send(bytes("f", 'utf-8'))
            # remove from dictionary
            dictionary_id[id_data][computer_number].remove(change)

        client_socket.send(bytes("x", 'utf-8'))