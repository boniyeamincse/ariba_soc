# Ariba SOC Remote Deployment Package (Production Ready)

এই ফোল্ডারটি (`remoted/`) সম্পূর্ণ সেলফ-কন্টেইন্ড (Self-Contained)। **রিমোট সার্ভারে কোনো Django পাইথন কোড পাঠানো ছাড়াই** সরাসরি Docker Hub থেকে প্রি-বিল্ট ইমেজ নিয়ে পুরো Ariba SOC + Wazuh ক্লাস্টার চালু করতে এটি তৈরি করা হয়েছে।

---

## 📦 এতে কী কী অন্তর্ভুক্ত রয়েছে?
- **`docker-compose.yml`**: শুধুমাত্র অফিশিয়াল ও ডকারহাব ইমেজ (`boniyeamin/ariba_soc-web`, `boniyeamin/ariba_soc-scheduler`, `wazuh/*`, `postgres:15`, `redis:7`, `nginx:1.27`) ব্যবহার করে সার্ভিস রান করে। কোনো লোকাল কোড বিল্ডের প্রয়োজন নেই।
- **`generate-indexer-certs.yml`**: সার্ভারে স্বয়ংক্রিয়ভাবে Wazuh অভ্যন্তরীণ SSL সার্টিফিকেট তৈরি করে।
- **`config/`**: Nginx কনফিগারেশন, Wazuh Manager রুলস/লিস্ট, Indexer কনফিগারেশন ও ড্যাশবোর্ড কনফিগ।
- **`.env.example`**: সমস্ত প্রয়োজনীয় পাসওয়ার্ড ও পোর্ট সেটিং সহ সম্পূর্ণ কনফিগারেশন টেমপ্লেট।
- **`scripts/setup.sh`**: এক ক্লিকে সম্পূর্ণ সেটআপ (কার্নেল চেক, SSL সার্টিফিকেট তৈরি, ইমেজ পুল, সার্ভিস আপ ও ডিফল্ট ডেটা সিডিং)।
- **`scripts/health-check.sh`**: সার্ভিস এবং API গুলোর লাইভ স্ট্যাটাস চেক।
- **`scripts/update.sh`**: নতুন Docker Hub ইমেজ পুশ হলে সার্ভারে লাইভ আপডেট।
- **`scripts/backup.sh` ও `restore.sh`**: ডেটাবেস এবং কনফিগারেশন ব্যাকআপ ও রিস্টোর।

---

## 🚀 কীভাবে সার্ভারে পাঠাবেন ও চালাবেন?

### পদ্ধতি ১: লোকাল পিসি থেকে সরাসরি পাঠানো (সবচেয়ে সহজ)
আপনার লোকাল পিসি থেকে এই কমান্ডটি দিন:
```bash
cd /home/boni/Desktop/ariba_soc-main/remoted
./deploy-to-server.sh username@your_server_ip
```
*(এটি কোনো সোর্স কোড ছাড়া শুধু কনফিগ ও স্ক্রিপ্টগুলো রিমোট সার্ভারে `~/ariba_soc_deploy` ফোল্ডারে পাঠাবে)*

---

### পদ্ধতি ২: রিমোট সার্ভারে সেটআপ সম্পন্ন করা

১. রিমোট সার্ভারে SSH দিয়ে লগইন করুন:
```bash
ssh username@your_server_ip
cd ~/ariba_soc_deploy
```

২. যদি রিমোট সার্ভারে Docker ইনস্টল না থাকে:
```bash
sudo ./scripts/install-docker.sh
```

৩. পরিবেশ ভেরিয়েবল সেট করুন:
```bash
cp .env.example .env
nano .env
```
*(প্রয়োজন অনুযায়ী `DJANGO_SECRET_KEY`, ডাটাবেস পাসওয়ার্ড, ডোমেইন বা আইপি পরিবর্তন করুন)*

৪. ওয়ান-ক্লিক সেটআপ রান করুন:
```bash
./scripts/setup.sh
```

---

## 🌐 সার্ভিস অ্যাক্সেস URLs

সেটআপ শেষ হলে নিচের লিঙ্কগুলোতে অ্যাক্সেস করতে পারবেন:

| সার্ভিস | URL | ডিফল্ট ক্রেডেনশিয়াল |
| :--- | :--- | :--- |
| **Ariba SOC Platform** | `http://<SERVER_IP>:80` | `admin` / `Admin_SOC_Pass123!` (বা আপনার `.env` অনুযায়ী) |
| **Wazuh Dashboard** | `https://<SERVER_IP>:8443` | `admin` / `.env`-এ দেওয়া পাসওয়ার্ড |
| **Wazuh Manager API** | `https://<SERVER_IP>:55000` | `wazuh-wui` / `.env`-এ দেওয়া পাসওয়ার্ড |

---

## 🛠️ প্রয়োজনীয় কমান্ডসমূহ

- **স্ট্যাটাস এবং হেলথ চেক:**
  ```bash
  ./scripts/health-check.sh
  ```
- **লগ দেখতে:**
  ```bash
  docker compose logs -f web
  docker compose logs -f scheduler
  ```
- **নতুন কোড/ইমেজ আপডেট করতে:**
  *(লোকালে কোড পরিবর্তন করে `push-dockerhub.sh` করার পর রিমোটে শুধু এটি রান করবেন)*
  ```bash
  ./scripts/update.sh
  ```
- **ব্যাকআপ নিতে:**
  ```bash
  ./scripts/backup.sh
  ```
- **সার্ভিস বন্ধ করতে:**
  ```bash
  docker compose down
  ```
