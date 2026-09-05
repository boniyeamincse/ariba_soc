import os
import sys
import pexpect

host = os.environ.get('WAZUH_SSH_HOST')
user = os.environ.get('WAZUH_SSH_USER')
password = os.environ.get('WAZUH_SSH_PASSWORD')
sudo_password = os.environ.get('WAZUH_SSH_SUDO_PASSWORD', password)

if not host or not user or not password:
    sys.exit('Set WAZUH_SSH_HOST, WAZUH_SSH_USER, WAZUH_SSH_PASSWORD env vars before running.')

try:
    print("Connecting...")
    child = pexpect.spawn(f'ssh -o StrictHostKeyChecking=no {user}@{host}', encoding='utf-8')
    child.logfile = sys.stdout

    idx = child.expect(['(?i)password:', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
    if idx == 0:
        child.sendline(password)
    else:
        sys.exit(1)

    child.expect([r'\$', r'#', r'>'], timeout=10)

    print("Switching to root...")
    child.sendline('sudo su')
    idx = child.expect(['(?i)password', r'#'], timeout=5)
    if idx == 0:
        child.sendline(sudo_password)
        child.expect(r'#', timeout=5)

    print("Checking Firewall...")
    # Check if firewalld is running
    child.sendline('systemctl is-active firewalld')
    idx = child.expect([r'active', r'unknown', r'inactive', r'#'], timeout=5)
    if idx == 0:
        child.expect(r'#')
        child.sendline('firewall-cmd --zone=public --add-port=9200/tcp --permanent')
        child.expect(r'#')
        child.sendline('firewall-cmd --reload')
        child.expect(r'#')

    # Check if ufw is running
    child.sendline('ufw status')
    idx = child.expect([r'Status: active', r'Status: inactive', r'command not found', r'#'], timeout=5)
    if idx == 0:
        child.expect(r'#')
        child.sendline('ufw allow 9200/tcp')
        child.expect(r'#')

    # Check iptables
    child.sendline('iptables -I INPUT -p tcp -m tcp --dport 9200 -j ACCEPT')
    child.expect(r'#', timeout=5)

    print("Finished successfully.")
    child.sendline('exit')
    child.sendline('exit')
except Exception as e:
    print(f"Error occurred: {str(e)}")
