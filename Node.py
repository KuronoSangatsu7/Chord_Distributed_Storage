import zlib
import sys
import grpc
import os
import chord_pb2
import chord_pb2_grpc
from concurrent import futures
from contextlib import suppress

node_key_dict = {}
node_id = 0
node_predecessor = ()
M = 0

def get_keys():
    return node_key_dict

def get_finger_table():
    return node_finger_table

def update_finger_table():
    if not node_registered:
        return
    
    params = chord_pb2.PopulateFingerTableRequest(node_id=node_id)
    
    response = registry_stub.PopulateFingerTable(params)

    global node_predecessor 
    node_predecessor = (response.predecessor.node_id, response.predecessor.ip_addr_port_num)

    global node_finger_table
    node_finger_table = []
    for entry in response.finger_table:
        node_finger_table.append((entry.node_id, entry.ip_addr_port_num))

def in_range(num, start, end):
    if start >= end:
        if num < start and start <= num + 2** M < end + 2** M:
            return True
        elif num >= start and start <= num < end + 2** M:
            return True
        return False
    else:
        return start <= num < end

def in_range1 (num, start, end):
    if start >= end:
        if num < start and start < num + 2** M <= end + 2** M:
            return True
        elif num >= start and start < num <= end + 2** M:
            return True
        return False
    else:
        return start < num <= end

def hash_key(key):
    hash_value = zlib.adler32(key.encode())
    target_id = hash_value % (2 ** M)
    return target_id

def lookup(key):
    target_id = hash_key(key)
    succ = node_finger_table[0][0]

    if in_range1 (target_id, node_predecessor[0], node_id):
        return (True, node_id)
    elif in_range1 (target_id, node_id, succ):
        return (False, node_finger_table[0][1])
    else:
        for i in range(len(node_finger_table)):
            if in_range(target_id, node_finger_table[i][0], node_finger_table[i+1][0]):
                return (False, node_finger_table[i][1])

def save(key, text):
    global node_key_dict
    found = lookup(key)
    if found[0] == True:
        if key not in node_key_dict:
            node_key_dict[key] = text
            return (True, found[1])
        else:
            return (False, f"{key} already exists in node {found[1]}")
    else:
        return forward_save(key, text, found[1])

def forward_save(key, text, target_ip_address_port_num):
    channel = grpc.insecure_channel(target_ip_address_port_num)
    node_stub = chord_pb2_grpc.ChordServiceStub(channel)

    params = chord_pb2.SaveRequest(key=key, text=text)

    response = node_stub.Save(params)

    if response.successful == True:
        return (True, response.node_id)
    
    else:
        return (False, response.error_message)

def remove(key):
    global node_key_dict
    found = lookup(key)
    if found[0] == True:
        if key in node_key_dict:
            del node_key_dict[key]
            return (True, found[1])
        else:
            return (False, f"{key} does not exist in node {found[1]}")
    else:
        return forward_remove(key, found[1])

def forward_remove(key, target_ip_address_port_num):
    channel = grpc.insecure_channel(target_ip_address_port_num)
    node_stub = chord_pb2_grpc.ChordServiceStub(channel)

    params = chord_pb2.RemoveRequest(key=key)

    response = node_stub.Remove(params)

    if response.successful == True:
        return (True, response.node_id)
    
    else:
        return (False, response.error_message)

def find(key):
    found = lookup(key)
    if found[0] == True:
        if key in node_key_dict:
            return (True, found[1], f"{node_ip_address}:{node_port_number}")
        else:
            return (False, f"{key} does not exist in node {found[1]}")
    else:
        return forward_find(key, found[1])

def forward_find(key, target_ip_address_port_num):
    channel = grpc.insecure_channel(target_ip_address_port_num)
    node_stub = chord_pb2_grpc.ChordServiceStub(channel)

    params = chord_pb2.FindRequest(key=key)

    response = node_stub.Find(params)

    if response.successful == True:
        return (True, response.node_id, response.ip_addr_port_num)
    
    else:
        return (False, response.error_message)

def register_self():
    params = chord_pb2.RegisterRequest(ip_address=node_ip_address, port_number = node_port_number)

    response = registry_stub.Register(params)

    if response.node_id !=-1:
        global node_id, M, node_registered
        node_registered = True
        node_id = response.node_id
        M = response.m
    
    else:
        print(f"{response.error_message}")
        terminate()
    
def get_successor_keys():
    target_ip_address_port_num = node_finger_table[0][1]

    channel = grpc.insecure_channel(target_ip_address_port_num)
    node_stub = chord_pb2_grpc.ChordServiceStub(channel)

    params = chord_pb2.GetKeysRequest()

    response = node_stub.GetKeys(params)

    successor_keys = {}

    for key in response.keys:
        successor_keys[key.key] = key.value
    
    return successor_keys

def remove_disowned_keys(list_of_keys):
    global node_key_dict
    for key in list_of_keys:
        del node_key_dict[key]

def get_own_keys():
    if node_id == node_finger_table[0][0]:
        return

    global node_key_dict
    successor_keys = get_successor_keys()
    successor_disowned_keys = []
    for key in successor_keys.keys():
        if hash_key(key) <= node_id:
            node_key_dict[key]= successor_keys[key]
            successor_disowned_keys.append(key)
    
    successor_ip_address_port_number = node_finger_table[0][1]

    channel = grpc.insecure_channel(successor_ip_address_port_number)
    node_stub = chord_pb2_grpc.ChordServiceStub(channel)

    params = chord_pb2.RemoveOwnKeysRequest()

    params.keys.extend(successor_disowned_keys)

    node_stub.RemoveOwnKeys(params)

def quit():
        # The node Deregistering itself
        params = chord_pb2.DeregisterRequest()

        params.node_id = node_id

        registry_stub.Deregister(params)
        
        params = chord_pb2.PromptUpdateRequest()

        if node_id != node_predecessor[0]:
            # Notifying Predecessor
            channel = grpc.insecure_channel(node_predecessor[1])
            node_stub = chord_pb2_grpc.ChordServiceStub(channel)

            node_stub.PromptUpdate(params)

        if node_id != node_finger_table[0][0]:
            # Notifying Successor
            channel = grpc.insecure_channel(node_finger_table[0][1])
            node_stub = chord_pb2_grpc.ChordServiceStub(channel)

            node_stub.PromptUpdate(params)
            # Handing over node's keys to Successor
            for key in node_key_dict:
                forward_save(key, node_key_dict[key], node_finger_table[0][1])

def terminate():
    print("Node is shutting down...")
    os._exit(0)

class ChordService(chord_pb2_grpc.ChordServiceServicer):
    def Save(self, request, context):
        key = request.key
        text = request.text

        saved = save(key, text)

        response = chord_pb2.SaveResponse()

        if saved[0] == True:
            response.successful = True
            response.node_id = saved[1]
        
        else:
            response.successful = False
            response.error_message = saved[1]
        
        return response
    
    def Remove(self, request, context):
        key = request.key

        removed = remove(key)

        response = chord_pb2.RemoveResponse()

        if removed[0] == True:
            response.successful = True
            response.node_id = removed[1]
        
        else:
            response.successful = False
            response.error_message = removed[1]
        
        return response

    def Find(self, request, context):
        key = request.key

        found = find(key)
        
        response = chord_pb2.FindResponse()

        if found[0] == True:
            response.successful = True
            response.node_id = found[1]
            response.ip_addr_port_num = found[2]
        
        else:
            response.successful = False
            response.error_message = found[1]
        
        return response

    def GetFingerTable(self, request, context):
        response = chord_pb2.GetFingerTableResponse()

        finger_table = [chord_pb2.IDStringPair(node_id=element[0], ip_addr_port_num=element[1]) for element in node_finger_table]

        response.finger_table.extend(finger_table)

        return response
    
    def GetKeys(self, request, context):
        response = chord_pb2.GetKeysResponse()

        keys = [chord_pb2.KeyValuePair(key=key, value=node_key_dict[key]) for key in node_key_dict.keys()]

        response.keys.extend(keys)

        return response

    def RemoveOwnKeys(self, request, context):
        disowned_keys = [key for key in request.keys]

        remove_disowned_keys(disowned_keys)

        response = chord_pb2.RemoveOwnKeysResponse()

        return response
    
    def GetSelfType(self, request, context):
        response = chord_pb2.GetSelfTypeResponse()

        response.type = "Node"

        return response
    
    def GetID(self, request, context):
        response = chord_pb2.GetIDResponse()

        response.id = node_id

        return response
    
    def PromptUpdate(self, request, context):
        response = chord_pb2.PromptUpdateResponse()

        update_finger_table()

        return response

def init():
    registry_address_port = sys.argv[1]
    node_address_port = sys.argv[2]

    global registry_ip_address
    registry_ip_address = registry_address_port.split(":")[0]
    global registry_port_number 
    registry_port_number = int(registry_address_port.split(":")[1])


    global node_ip_address
    node_ip_address = node_address_port.split(":")[0]
    global node_port_number
    node_port_number = int(node_address_port.split(":")[1])

    global registry_stub

    channel = grpc.insecure_channel(f"{registry_ip_address}:{registry_port_number}")
    registry_stub = chord_pb2_grpc.ChordServiceStub(channel)

    try:
        register_self()

        update_finger_table()

        get_own_keys()
    except grpc.RpcError:
            print("Registry is offline.")
            terminate()

    print("Node joined and finger table populated.")
    print(f"assigned node_id={node_id}, successor_id={node_finger_table[0][0]}, predecessor_id={node_predecessor[0]}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chord_pb2_grpc.add_ChordServiceServicer_to_server(ChordService(), server)
    server.add_insecure_port(f"{node_ip_address}:{node_port_number}")
    server.start()

    while True:
        try:
            server.wait_for_termination(1)
            update_finger_table()
        except grpc.RpcError:
            print("Registry is offline.")
            terminate()

        except KeyboardInterrupt:
            quit()
            print("Node left the ring.")
            terminate()

if __name__ == "__main__":
    init()