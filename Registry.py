import random
import sys
import grpc
import chord_pb2
import chord_pb2_grpc
from concurrent import futures

chord_dict = {}

def register (ipaddr, port):
    if len(chord_dict) == (2**M):
        return (-1, "The chord is already full")
    id = 0
    random.seed(0)
    while True:
        id = random.randint(0, 2**M-1)
        if id not in chord_dict:
            chord_dict[id]= (ipaddr, port)
            break
    return (id, M)

def deregister (id):
    if id not in chord_dict:
        return (False, "No such id")
    del chord_dict[id]
    return (True, f"The id {id} has been removed")

def find(p):
    if p in chord_dict:
        return p
    return find((p+1) % (2**M))
    
def find_pred(p):
    if p in chord_dict:
        return (p, f"{chord_dict[p][0]}:{chord_dict[p][1]}")
    return find_pred((p-1 + 2**M) % (2**M))

def populate_finger_table (id):
    #this function might be wrong
    FT = []
    for i in range(M):
        newId = find((id+2**i) % (2**M))
        FT.append((newId, f"{chord_dict[newId][0]}:{chord_dict[newId][1]}"))

    FT = list(dict.fromkeys(FT))
    return find_pred((id-1 + 2**M) % (2**M)), FT

def get_chord_info ():
    return [(x, f"{chord_dict[x][0]}:{chord_dict[x][1]}") for x in chord_dict.keys()]

class ChordService(chord_pb2_grpc.ChordServiceServicer):
    def Register(self, request, context):
        ip_address = request.ip_address
        port_number = request.port_number

        registration = register(ip_address, port_number)

        response = chord_pb2.RegisterResponse()

        if registration[0] == -1:
            response.node_id = -1
            response.error_message = registration[1]
        
        else:
            response.node_id = registration[0]
            response.m = registration[1]
        
        return response
    
    def Deregister(self, request, context):
        node_id = request.node_id

        deregistration = deregister(node_id)

        response = chord_pb2.DeregisterResponse()

        response.successful = deregistration[0]
        response.message = deregistration[1]

        return response

    def PopulateFingerTable(self, request, context):
        node_id = request.node_id

        population = populate_finger_table(node_id)

        response = chord_pb2.PopulateFingerTableResponse()
        
        predecessor = chord_pb2.IDStringPair(node_id=population[0][0], ip_addr_port_num=population[0][1])

        response.predecessor.CopyFrom(predecessor)
        
        finger_table = [chord_pb2.IDStringPair(node_id=element[0], ip_addr_port_num=element[1]) for element in population[1]]

        response.finger_table.extend(finger_table)
        
        return response

    def GetChordInfo(self, request, context):
        chord = get_chord_info()

        response = chord_pb2.GetChordInfoResponse()

        chord_ring = [chord_pb2.IDStringPair(node_id=element[0], ip_addr_port_num=element[1]) for element in chord]
        
        response.chord_ring.extend(chord_ring)

        return response
    
    def GetSelfType(self, request, context):
        response = chord_pb2.GetSelfTypeResponse()

        response.type = "Registry"

        return response


def init():

    global registry_address_port
    registry_address_port = sys.argv[1]
    global M
    M = int(sys.argv[2])

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chord_pb2_grpc.add_ChordServiceServicer_to_server(ChordService(), server)
    
    server.add_insecure_port(f"{registry_address_port}")
    server.start()
    print("Registry server started.")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Registry server shutting down...")

if __name__ == "__main__":
    init()