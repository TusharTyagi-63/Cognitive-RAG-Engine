import socket

def check_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"Port {port} is OPEN on {host}")
        else:
            print(f"Port {port} is CLOSED on {host}")
        sock.close()
    except Exception as e:
        print(f"Error checking {host}:{port} -> {e}")

check_port('aws-1-ap-southeast-1.pooler.supabase.com', 6543)
check_port('aws-1-ap-southeast-1.pooler.supabase.com', 5432)
check_port('db.lneaumecnqrbywitjkya.supabase.co', 5432)
