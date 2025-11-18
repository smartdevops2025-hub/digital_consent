import socket

def check_port(port=5000):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', port))
        sock.close()
        print(f"✅ Port {port} is available")
        return True
    except OSError as e:
        print(f"❌ Port {port} is blocked: {e}")
        print("\n💡 Quick Solutions:")
        print("1. Try using port 8080 instead")
        print("2. Run Command Prompt as Administrator")
        print("3. Configure Windows Firewall")
        return False

if __name__ == "__main__":
    check_port(5000)
    input("\nPress Enter to exit...")