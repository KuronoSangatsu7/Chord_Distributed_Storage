import grpc
import chord_pb2
import chord_pb2_grpc
import os

stub = None

def parse_user_input(message):
    command = message.split(" ")[0]
    parsed_message = message.split(" ")

    if command == "connect":
        return ("Connect", parsed_message[1])
    elif command == "get_info":
        return ("Info", "info")
    elif command == "save":
        return ("Save", parsed_message[1].strip('"'), " ".join(parsed_message[2:]))
    elif command == "find":
        return ("Find", parsed_message[1])
    elif command == "remove":
        return ("Remove", parsed_message[1])
    elif command == "quit":
        return ("Quit", "quit")
    else:
        return ("Invalid", "invalid")

def connect(ip_addr_port_num):
    global connected_to
    global connected_node_id
    global stub

    channel = grpc.insecure_channel(ip_addr_port_num)
    stub = chord_pb2_grpc.ChordServiceStub(channel)
    try:
        params = chord_pb2.GetSelfTypeRequest()
        response = stub.GetSelfType(params)
    except grpc.RpcError:
        print("Target is offline. Please make sure the target is online before connecting, or check the validity of the IP:Port combination provided.")
        return

    connected_to = response.type

    if connected_to == "Node":
        params = chord_pb2.GetIDRequest()
        response = stub.GetID(params)
        connected_node_id = response.id

    print (f"Connected to {connected_to}")

def get_info():
    if stub is None:
        print("Please connect to a target before issuing commands.")
        return

    if connected_to == "Node":
        try:
            params = chord_pb2.GetFingerTableRequest()
            response = stub.GetFingerTable(params)
        except grpc.RpcError:
            print("Node has gone offline. Please connect to a different node before issuing a command.")
            return

        print(f"Node id: {connected_node_id}")

        print("Finger table:")
        for node in response.finger_table:
            print(f"{node.node_id}: {node.ip_addr_port_num}")
    else:
        try:
            params = chord_pb2.GetChordInfoRequest()
            response = stub.GetChordInfo(params)
        except grpc.RpcError:
            ("Registry has gone offline. Please make sure the registry is online before issuing a command.")
            return
        
        for node in response.chord_ring:
            print(f"{node.node_id}: {node.ip_addr_port_num}")

def save(key, text):
    if stub is None:
        print("Please connect to a target before issuing commands.")
        return
    try:
        params = chord_pb2.SaveRequest(key=key, text=text)
        response = stub.Save(params)
    except grpc.RpcError:
            print("Node has gone offline. Please connect to a different node before issuing a command.")
            return

    if response.successful == True:
        print(f"True, {key} has been saved in node {response.node_id}")
    
    else:
        print(f"False, {response.error_message}")
    
def remove(key):
    if stub is None:
        print("Please connect to a target before issuing commands.")
        return
    try:
        params = chord_pb2.RemoveRequest(key=key)
        response = stub.Remove(params)
    except grpc.RpcError:
            print("Node has gone offline. Please connect to a different node before issuing a command.")
            return

    if response.successful == True:
        print(f"True, {key} has been removed from node {response.node_id}")
    
    else:
        print(f"False, {response.error_message}")

def find(key):
    if stub is None:
        print("Please connect to a target before issuing commands.")
        return
    try:
        params = chord_pb2.FindRequest(key=key)
        response = stub.Find(params)
    except grpc.RpcError:
            print("Node has gone offline. Please connect to a different node before issuing a command.")
            return

    if response.successful == True:
        print(f"True, {key} is saved in node {response.node_id}")
    
    else:
        print(f"False, {response.error_message}")

def terminate():
    print("Client is shutting down...")
    os._exit(0)

def init():
    while True:
        try:
            user_input = input(">")
            parsed_input = parse_user_input(user_input)

            message_type = parsed_input[0]

            if message_type == "Connect":
                connect(parsed_input[1])
            elif message_type == "Info":
                get_info()
            elif message_type == "Save":
                save(parsed_input[1], parsed_input[2])
            elif message_type == "Find":
                find(parsed_input[1])
            elif message_type == "Remove":
                remove(parsed_input[1])
            elif message_type == "Quit":
                terminate()
            else:
                print("Invalid command! Please try again.")

        except KeyboardInterrupt:
            print("Use 'quit' to terminate the client program")

if __name__ == "__main__":
    init()