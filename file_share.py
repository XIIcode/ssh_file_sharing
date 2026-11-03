import os
import socket
import struct
import sys
import threading
import zipfile

PORT = 6669

def start_receiver():
  """Starts a server to receive incoming files and folders."""
  server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind(("0.0.0.0", PORT))
  server.listen(5)

  local_ip = socket.gethostbyname(socket.gethostname())
  print(f"\n\033[92m[*] File Receiver Server started!\033[0m")
  print(f"\033[96m[*] Tell others to send files to your IP: {local_ip}\033[0m")
  print("[*] Waiting for incoming files... Press Ctrl+C to stop.\n")

  try:
    while True:
      conn, addr = server.accept()
      try:
        # Read protocol header: [filename_length][filename][filesize]
        fn_len_data = conn.recv(4)
        if not fn_len_data:
          conn.close()
          continue
        
        fn_len = struct.unpack("!I", fn_len_data)[0]
        filename = conn.recv(fn_len).decode('utf-8')
        filesize = struct.unpack("!Q", conn.recv(8))[0]

        save_path = f"received_{filename}"
        print(f"[*] Receiving '{filename}' ({filesize} bytes) from {addr[0]}...")

        received = 0
        with open(save_path, "wb") as f:
          while received < filesize:
            chunk = conn.recv(min(4096, filesize - received))
            if not chunk:
              break
            f.write(chunk)
            received += len(chunk)

        print(f"\033[92m[+] Successfully saved as '{save_path}'\033[0m\n")
      except Exception as e:
        print(f"\033[91m[!] Error receiving file: {e}\033[0m")
      finally:
        conn.close()
  except KeyboardInterrupt:
    print("\n\033[91m[*] Stopping receiver server...\033[0m")
    server.close()

def send_item(target_ip, path):
  """Sends a file or folder (automatically zipped) to a target IP."""
  if not os.path.exists(path):
    print(f"\033[91m[!] Error: Path '{path}' does not exist.\033[0m")
    return

  is_dir = os.path.isdir(path)
  actual_path = path
  zip_filename = None

  # If it's a folder, zip it first so it can be sent as a single file
  if is_dir:
    zip_filename = f"{os.path.basename(os.path.normpath(path))}.zip"
    print(f"[*] Zipping folder '{path}' into '{zip_filename}'...")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
      for root, _, files in os.walk(path):
        for file in files:
          full_p = os.path.join(root, file)
          arc_p = os.path.relpath(full_p, start=path)
          zipf.write(full_p, arc_p)
    actual_path = zip_filename

  filename = os.path.basename(actual_path)
  filesize = os.path.getsize(actual_path)

  print(f"[*] Connecting to {target_ip}:{PORT}...")
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((target_ip, PORT))

    # Send header
    fn_bytes = filename.encode('utf-8')
    header = struct.pack("!I", len(fn_bytes)) + fn_bytes + struct.pack("!Q", filesize)
    s.sendall(header)

    print(f"[*] Sending '{filename}' ({filesize} bytes)...")
    with open(actual_path, "rb") as f:
      while chunk := f.read(4096):
        s.sendall(chunk)

    s.close()
    print(f"\033[92m[+] Transfer complete for '{filename}'!\033[0m")

  except Exception as e:
    print(f"\033[91m[!] Connection/Transfer failed: {e}\033[0m")

  # Clean up temporary zip file if a directory was sent
  if is_dir and zip_filename and os.path.exists(zip_filename):
    os.remove(zip_filename)

if __name__ == "__main__":
  print("\033[96m=== Simple LAN File & Folder Sharing Tool ===\033[0m")
  print("1. Receive Files (Start Server)")
  print("2. Send File or Folder")
  choice = input("Select mode (1 or 2): ").strip()

  if choice == "1":
    start_receiver()
  elif choice == "2":
    ip = input("Enter receiver's IP address: ").strip()
    path = input("Enter path to file or folder to send: ").strip()
    # Strip wrapping quotes if user dragged & dropped path into terminal
    path = path.strip('"').strip("'")
    send_item(ip, path)
  else:
    print("\033[91mInvalid choice.\033[0m")