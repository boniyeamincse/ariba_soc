# 📘 Ariba SOC: Wazuh Agent Deployment & Configuration Guideline
### (এন্ডপয়েন্ট ও ওয়েব সার্ভার এজেন্ট সেটআপ এবং মনিটরিং গাইডলাইন)

এই ডিরেক্টরিতে আপনার যেকোনো লিনাক্স সার্ভার (Ubuntu, Debian, RHEL, CentOS ইত্যাদি) কে **Ariba SOC** এবং **Wazuh Cluster**-এর সাথে যুক্ত করে ২৪/৭ মনিটর করার সমস্ত কনফিগারেশন, অটোমেশন স্ক্রিপ্ট এবং গাইডলাইন রয়েছে।

---

## 📂 ডিরেক্টরি কাঠামো (Directory Overview)

```text
agent/
├── GUIDE.md                             # এই পূর্ণাঙ্গ গাইডলাইন ফাইল
├── README.md                            # ডিরেক্টরি পরিচিতি
├── config/
│   └── ossec.conf                       # এজেন্টের ফুল প্রোডাকশন কনফিগারেশন টেমপ্লেট
├── auditd/
│   └── wazuh-php2shell.rules            # লিনাক্স অডিট রুলস (EUID 33 / www-data ও কমান্ড ট্র্যাকিং)
├── sca/
│   └── php2shell_mitigations.yml        # কাস্টম SCA পলিসি (PHP.ini দুর্বলতা অডিট)
└── scripts/
    ├── install-agent.sh                 # ১-ক্লিকে এজেন্ট ইনস্টল, এনরোল ও হার্ডেনিং স্ক্রিপ্ট
    └── verify-agent.sh                  # এজেন্টের কানেকশন ও হেলথ ভেরিফিকেশন টুল
```

---

## 🚀 পদ্ধতি ১: অটোমেটেড ১-কমান্ড ইনস্টলেশন (Recommended)

আপনার টার্গেট লিনাক্স সার্ভারে (যেমন ওয়েব সার্ভার) `agent/` ফোল্ডারটি কপি করুন অথবা স্ক্রিপ্টটি ডাউনলোড করে রান করুন:

```bash
# কমান্ড সিনট্যাক্স:
sudo ./scripts/install-agent.sh <WAZUH_MANAGER_IP> [AGENT_NAME]

# উদাহরণ (রিমোট ম্যানেজারের আইপি দিয়ে):
sudo ./scripts/install-agent.sh 10.24.66.2 web-server-01
```

### এই স্ক্রিপ্ট স্বয়ংক্রিয়ভাবে যা যা করে:
1. Wazuh অফিসিয়াল প্যাকেজ রিপোজিটরি এবং GPG কী যুক্ত করে।
2. `wazuh-agent` এবং `auditd` প্যাকেজ ইনস্টল করে।
3. `/var/ossec/etc/ossec.conf` ফাইলে ম্যানেজার আইপি, রিয়েল-টাইম FIM (`/var/www/html`), Apache/Nginx এরর ও এক্সেস লগ যুক্ত করে।
4. `php2shell_mitigations.yml` ফাইলটি `/var/ossec/etc/custom-sca-files/`-এ বসিয়ে দেয়।
5. `wazuh-php2shell.rules` ফাইলটি `/etc/audit/rules.d/`-এ রেখে `augenrules --load` এক্সিকিউট করে।
6. সার্ভিসগুলো সক্রিয় করে ম্যানেজারের সাথে হ্যান্ডশেক নিশ্চিত করে।

---

## 🛠️ পদ্ধতি ২: ম্যানুয়াল ইনস্টলেশন (Manual Step-by-Step)

### ধাপ ১: Wazuh Agent ইনস্টল করা
**Ubuntu / Debian-এ:**
```bash
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import
chmod 644 /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list
sudo apt update
sudo WAZUH_MANAGER="10.24.66.2" apt install -y wazuh-agent auditd
```

---

### ধাপ ২: ossec.conf কনফিগারেশন বসানো
`agent/config/ossec.conf` ফাইলটি ওপেন করে `<address>WAZUH_MANAGER_IP</address>` এর জায়গায় আপনার ম্যানেজারের IP দিন (যেমন: `10.24.66.2`)।
এরপর সার্ভারে কপি করুন:
```bash
sudo cp agent/config/ossec.conf /var/ossec/etc/ossec.conf
sudo chown root:wazuh /var/ossec/etc/ossec.conf
sudo chmod 640 /var/ossec/etc/ossec.conf
```

#### এতে অন্তর্ভুক্ত গুরুত্বপূর্ণ ফিচারসমূহ:
- **Web Root FIM:** `/var/www/html` ডিরেক্টরিতে কোনো ওয়েবশেল (`.php`, `.phtml`, `.phar`) পড়ামাত্র রিয়েল-টাইম অ্যালার্ট।
- **Web Logs:** Apache/Nginx error.log এবং access.log স্বয়ংক্রিয় মনিটরিং।
- **Process Auditing:** Auditd ইন্টিগ্রেশন।

---

### ধাপ ৩: কাস্টম SCA পলিসি যুক্ত করা
```bash
sudo mkdir -p /var/ossec/etc/custom-sca-files
sudo cp agent/sca/php2shell_mitigations.yml /var/ossec/etc/custom-sca-files/
sudo chown -R root:wazuh /var/ossec/etc/custom-sca-files/
sudo chmod 640 /var/ossec/etc/custom-sca-files/*.yml
```

---

### ধাপ ৪: Auditd রুলস সক্রিয় করা
```bash
sudo cp agent/auditd/wazuh-php2shell.rules /etc/audit/rules.d/
sudo augenrules --load
# যাচাই করুন:
sudo auditctl -l | grep audit-wazuh-c
```

---

### ধাপ ৫: সার্ভিস রিস্টার্ট ও এনরোলমেন্ট
```bash
sudo systemctl daemon-reload
sudo systemctl enable wazuh-agent auditd
sudo systemctl restart wazuh-agent auditd
```

---

## 🔍 এজেন্টের হেলথ ভেরিফিকেশন (Health Check)

ইনস্টলেশন শেষে এন্ডপয়েন্ট সার্ভারে চালান:
```bash
sudo ./scripts/verify-agent.sh
```

যদি সব ঠিক থাকে, আপনি দেখতে পাবেন:
- `wazuh-agent daemon... ACTIVE & RUNNING`
- `Server Connection... CONNECTED`
- `auditd rules... LOADED`
- `Custom SCA Policy... EXISTS & ACCESSIBLE`
- `FIM web root... CONFIGURED (/var/www/html)`

---

## 🧪 সাইবার অ্যাটাক টেস্টিং (Detection Emulation)

### ১. মেমরি লিক / প্রি-কার্সর টেস্ট (PHP2Shell Rule 100200)
```bash
curl -s "http://localhost/php2shell-test.php"
```
➡️ **Ariba SOC ড্যাশবোর্ডে Rule 100200 (Level 7) অ্যালার্ট জেনারেট হবে।**

### ২. ওয়েব সার্ভার ইউজার দিয়ে কমান্ড এক্সিকিউশন (Rule 100210)
```bash
sudo -u www-data /bin/sh -c 'id; uname -a'
```
➡️ **Ariba SOC ড্যাশবোর্ডে Rule 100210 (Level 12) Critical অ্যালার্ট আসবে।**

### ৩. ওয়েব শেল ক্রিয়েশন টেস্ট (Rule 100220)
```bash
echo '<?php system($_GET["cmd"]); ?>' | sudo tee /var/www/html/test_shell.php
```
➡️ **Wazuh FIM রিয়েল-টাইমে ডিটেক্ট করবে এবং Rule 100220 (Level 12) অ্যালার্ট দিবে।**
*(টেস্ট শেষে ফাইলটি ডিলিট করতে ভুলবেন না: `sudo rm /var/www/html/test_shell.php`)*

---

## ❓ সাধারণ সমস্যা ও সমাধান (Troubleshooting)

1. **Agent সার্ভারের সাথে কানেক্ট হচ্ছে না (Disconnected):**
   - ম্যানেজারের পোর্ট ১৫১৪ ও ১৫১৫ ওপেন আছে কিনা চেক করুন:
     ```bash
     nc -zv <WAZUH_MANAGER_IP> 1514
     nc -zv <WAZUH_MANAGER_IP> 1515
     ```
   - ক্লায়েন্ট লগ দেখুন: `sudo tail -n 50 /var/ossec/logs/ossec.log`

2. **Web server log ফাইল পাওয়া যাচ্ছে না এরর:**
   - যদি সার্ভারে Nginx থাকে এবং Apache না থাকে, তবে `/var/ossec/etc/ossec.conf` থেকে অপ্রয়োজনীয় `<localfile>` ব্লকগুলো সরিয়ে দিন বা ফাইলের সঠিক পাথ উল্লেখ করুন।
