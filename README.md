### Chord Distributed Storage
This is a Python implementation of Chord, which is a Scalable Peer-to-peer Lookup Protocol. You can read more about it [here](https://pdos.csail.mit.edu/papers/ton:chord/paper-ton.pdf).

The main motivation behind Chord is that it _"adapts efficiently as nodes join and leave the system, and can answer queries even if the system is continuously changing. Results from theoretical analysis and simulations show that Chord is scalable: communication cost and the state maintained by each node scale logarithmically with the number of Chord nodes."_

### Tech Used:
- `Python`
- `Protocol Buffers`
- `gRPC`

### Usage:

Install and activate the virtual environment then compile the `.proto` file using:
        
    pip install virtualenv

    virtualenv venv

    source venv/bin/activate

    pip install -r requirements.txt

    python3 -m grpc_tools.protoc chord.proto --proto_path=. --python_out=. --grpc_python_out=.

The application consists of 2 main parts:

- Registry - `Registry.py`:

    The Registry is basically the main "hub" of the Chord system. It is responsible for regsitring and deregestring nodes as they enter and leave the distributed system as it holds a dictionary of `ID` and `IP_ADDRESS` `PORT_NUMBER` pairs of all registered nodes.

    To run the Registry, simply run an instance of `Registry.py` and pass it two command line arguments. The first one is `IP_ADDRESS:PORT_NUMBER` on which the Regsitry will run, and the second being a number `M` which is represents the maximum allowed number of nodes in the chord. 

    Example:

        python3 Registry.py 127.0.0.1:5000 5

- Node - `Node.py`:

    The Nodes are essentially the group of servers present in the Chord. They are able to join/leave the chord, communicate with the regsitry to obtain information about themselves/other nodes, as well as store and retrieve user data (key-value storage).

    To run a Node, simply run an instance of `Node.py` and pass it two command line arguemnts. The first one being `REGISTRY_IP_ADDRESS:REGISTRY_PORT_NUMBER` which indicates the ip address and port number on which the regsitry is currently running, and the second one being `IP_ADDRESS:PORT_NUMBER` which is the ip address and port number on which this node will run.

    Example of running 6 nodes:

        python3 Node.py 127.0.0.1:5000 127.0.0.1:5001
        python3 Node.py 127.0.0.1:5000 127.0.0.1:5002
        python3 Node.py 127.0.0.1:5000 127.0.0.1:5003
        python3 Node.py 127.0.0.1:5000 127.0.0.1:5004
        python3 Node.py 127.0.0.1:5000 127.0.0.1:5005
        python3 Node.py 127.0.0.1:5000 127.0.0.1:5006
    
- Client - `Client.py`:

    The Client in this case represents the user/tester. The Client can issue different commands to the Regsitry or any of the Nodes to obtain information about the Chord ring or store/retrieve/remove data from it. The commands are:

    - `connect IP_ADDRESS:PORT_NUMBER`: Connects to the corresponding Registry/Node and issues all subsequent commands to it and handles errors.

    - `get_info`: Sends a request to the currently connected Registry/Node to return the current structure (finger table) of the chord ring.

    - `save KEY VAL`: Asks the currently connected Node to save `VAL` to the distributed system under `KEY`.

    - `remove KEY`: Asks the currently connected Node to remove `KEY` along with its corresponding value from the distributed system.

    - `find KEY`: Asks the currently connected Node to find the Node which owns (stores) `KEY`.

    - `quit`: Terminates the client program.

    To run the client, simply run an instance of `Client.py`.

    Example:

        > connect 127.0.0.1:5000
        Connected to Registry
        > get_info
        24: 127.0.0.1:5001
        26: 127.0.0.1:5002
        2: 127.0.0.1:5003
        16: 127.0.0.1:5004
        31: 127.0.0.1:5005
        25: 127.0.0.1:5006

        > connect 127.0.0.1:5001
        Connected to Node
        > get_info
        Node id: 24
        Finger table:
        2: 127.0.0.1:5003
        16: 127.0.0.1:5004
        25: 127.0.0.1:5006
        26: 127.0.0.1:5002
        31: 127.0.0.1:5005

        > save “Chord” text for chord // KEY=Chord VAL="text for chord"
        True, Chord is saved in node 24

        > save “Chord” text for chord
        False, Chord already exists in node 24

        > save “Linux” linux text
        True, Linux is saved in node 25

        > save “GitHub” github text
        True, GitHub is saved in node 16

        > find Linux
        True, Linux is saved in node 25

        > remove Linux
        True, Linux is removed from node 25

        > find Linux
        False, Linux does not exist in node 25

### Author Contact Info:
    Linux Totanji
    Email: jaafarti@gmail.com
    Telegram: @KuroHata7

    Ahmad Haidar
    Email: togoyany@gmail.com
    Telegram: @XmtosX

##### P.S: This work was done as a solution to an assignment given to us as part of the Distributed and Network Programming course at IU.