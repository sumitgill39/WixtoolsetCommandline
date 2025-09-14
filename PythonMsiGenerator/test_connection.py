import socket
import requests
import time

def test_port(port=6000):
    """Test if port is available"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex(('localhost', port))
        if result == 0:
            print(f"✅ Port {port} is open and accessible")
            return True
        else:
            print(f"❌ Port {port} is not accessible (error: {result})")
            return False
    finally:
        sock.close()

def test_http_request():
    """Test HTTP request to the server"""
    try:
        response = requests.get('http://localhost:6000', timeout=5)
        print(f"✅ HTTP request successful: {response.status_code}")
        print(f"Content preview: {response.text[:100]}...")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ HTTP connection failed - server not responding")
        return False
    except requests.exceptions.Timeout:
        print("❌ HTTP request timed out")
        return False
    except Exception as e:
        print(f"❌ HTTP request failed: {e}")
        return False

if __name__ == '__main__':
    print("=== Connection Test ===")
    
    # Test port
    port_open = test_port(6000)
    
    if port_open:
        time.sleep(1)
        # Test HTTP
        test_http_request()
    else:
        print("Port is not open. Make sure Flask server is running:")
        print("py simple_test.py")