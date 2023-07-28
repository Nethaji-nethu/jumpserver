import paramiko
from threading import Thread, Lock, Event
import time
import colorama
from colorama import Fore, Style
import re
import sys

# Enter the servers and credentials
hosts = ['server1','server2']  # change the servers list
username = "user"  # use your username here
password = input(f'Enter password for {username} : ').strip()  # use your password here

channels = []
threads = []

failed_auth = []
succeeded_auth = []

# Create an SSH client and get a channel/pseudo terminal
def connect_get_terminal(host, username, password, channels):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=username, password=password)
        # Create a pseudo terminal
        channel = ssh.invoke_shell()
        # Wait until the prompt comes back
        time.sleep(1)
        channel.recv(9999)
        channel.send("\n")
        time.sleep(1)
        channels.append(channel)
        succeeded_auth.append(host)
    except Exception as e:
        failed_auth.append(host)
        print(f"Failed to connect to {host}: {str(e)}\n")

for host in hosts:
    t = Thread(target=connect_get_terminal, args=(host, username, password, channels))
    t.start()
    threads.append(t)

for thread in threads:
    thread.join()

if failed_auth:
    print(f'[-] Failed to connect to servers \n{failed_auth}\n')


# Function to switch the user to root from the m account user
def switch_user(server,channel,username,password):
    for command in ['sudo -i', 'id']:
        channel.send(command + "\n")
        while not channel.recv_ready():
            time.sleep(1)
        time.sleep(1)
        output = channel.recv(9999).decode('utf-8').strip()
        if f'password for {username}:' in output:
            # print('[+] Switching user..\n[+] Sending password..')
            channel.send(password + "\n")
            while not channel.recv_ready():
                time.sleep(0.1)
            output = channel.recv(9999).decode('utf-8').strip()
        if command == 'id':
            if 'uid=0(root)' in output:
                print(f'[+] {server} : Successfully switched to root..\n',end='')
            else:
                print(f'[-] {server} : Something went wrong.. Please check the code.\n',end='')
                # exit(0)
        time.sleep(0.5)

threads = []  # reset threads

# create new threads for switching to root
for server, channel in zip(succeeded_auth, channels):
    t = Thread(target=switch_user, args=(server,channel,username,password), name=server)
    t.start()
    threads.append(t)

for thread in threads:
    thread.join()

# Function to execute commands as root and capture the output for each server
def exec_cmd_as_root(channel, command, server):
    channel.send(command + '\n')
    while not channel.recv_ready():
        time.sleep(1)
    time.sleep(1)
    output = channel.recv(9999).decode().strip()

    # Remove ANSI escape codes and store the output in the corresponding server_output
    clean_output = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', output)
    server_output[server] = clean_output

# Initialize colorama
colorama.init()

threads = []

# Create a dictionary to map each server to its output
server_output = {server: '' for server in succeeded_auth}

#create jump server console
while True:
    if not channels:
        break
    command = input("\nJump-server:~> # ").strip()
    print('*'*50)
    if command.lower() in ['exit', 'quit', 'logout']:
        break

    # Create new threads for executing the command on each server
    for server, channel in zip(succeeded_auth, channels):
        t = Thread(target=exec_cmd_as_root, args=(channel, command, server), name=server)
        t.start()
        threads.append(t)

    # Wait for all threads to complete before moving on to the next command
    for thread in threads:
        thread.join()

    # Print the output for each server in order
    for server,output in server_output.items():
        print(f'{server}:~ # {output}\n')
        print('*'*50)

# Close pseudo terminals/channels
for channel in channels:
    channel.close()

# Deinitialize colorama
colorama.deinit()

#exit the system
sys.exit(0)
