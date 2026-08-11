import pexpect
import sys
import time

try:
    print("Connecting...")
    child = pexpect.spawn('ssh -o StrictHostKeyChecking=no infosec@10.24.66.2', encoding='utf-8')
    child.logfile = sys.stdout

    idx = child.expect(['(?i)password:', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
    if idx == 0:
        child.sendline('WazInf@#4321')
    else:
        print("Failed to get password prompt.")
        sys.exit(1)

    child.expect([r'\$', r'#', r'>'], timeout=10)
    
    print("Switching to root...")
    child.sendline('sudo su')
    idx = child.expect(['(?i)password', r'#'], timeout=5)
    if idx == 0:
        child.sendline('WazInf@#4321')
        child.expect(r'#', timeout=5)
        
    print("Applying config...")
    child.sendline("sed -i 's/^network.host:.*/network.host: 0.0.0.0/g' /etc/wazuh-indexer/opensearch.yml")
    child.expect(r'#', timeout=5)
    
    print("Checking config:")
    child.sendline("grep network.host /etc/wazuh-indexer/opensearch.yml")
    child.expect(r'#', timeout=5)
    
    print("Restarting service...")
    child.sendline('systemctl restart wazuh-indexer')
    child.expect(r'#', timeout=60)
    
    print("Checking status:")
    child.sendline('systemctl is-active wazuh-indexer')
    child.expect(r'#', timeout=5)
    
    child.sendline('exit')
    child.sendline('exit')
    print("Finished successfully.")
except Exception as e:
    print(f"Error occurred: {str(e)}")
