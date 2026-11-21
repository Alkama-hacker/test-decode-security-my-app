# RHK COMMUNITY — APK বিশ্লেষণ রিপোর্ট

**ফাইল:** `myapp.7z` → ভিতরে একটাই ফাইল: `base.apk`
**তারিখ:** ২০২৬-১১-২০

---

## ১. ফাইল ও প্যাকেজ এক নজরে

| বিষয় | মান |
|---|---|
| 7z ফাইলের SHA-256 | `2a0276644fa313e762b407a7992e7c4ab97d836994c85e0aa180fc74659c51a8` |
| base.apk SHA-256 | `9d9d626f4e360b8bf99d6125413c992362bf59c01fd82918b2d4533beafda5d6` |
| APK সাইজ | 57.1 MB (আনকমপ্রেসড ~69 MB) |
| অ্যাপের নাম | **RHK COMMUNITY** |
| প্যাকেজ | `space.manus.rhktrade.t060868234445631` |
| ভার্সন | 1.0.0 (versionCode 10000) |
| minSdk / targetSdk | 26 (Android 8.0) / 36 (Android 16) |
| ফ্রেমওয়ার্ক | **Expo SDK 57 / React Native** (Hermes bytocode, New Architecture) |
| ABI | arm64-v8a + armeabi-v7a (x86 নেই) |
| সাইনিং | v2 RSA, CN=**Manus App** (self-signed), শুধু v2 — v1/v3 নেই |

অ্যাপটি অরিজিনাল কোনো নেটিভ অ্যাপ নয় — এটি **Expo দিয়ে বানানো একটা "WebView wrapper"**। ভিতরে কোনো UI কোড নেই বললেই চলে; পুরো অ্যাপটা আসলে একটা `.php` সাইটকে WebView-এ লোড করে দেখায়, সাথে একটা "security gate" অ্যানিমেশন।

---

## ২. অ্যাপটা আসলে কী করে (কোড থেকে বের করা)

অ্যাপের ভিতরের JS engine (Hermes bytecode) ডিকম্পাইল করে পাওয়া যায়:

- **Approved URL:** `https://hasib-one-fire.top/mahim-user.php`
- **Approved host:** `hasib-one-fire.top`
- **originWhitelist:** `["https://hasib-one-fire.top/*"]`
- **Request timeout:** 8000 ms
- **আচরণ:** অ্যাপ খুললে ৫ ধাপের একটা "সিকিউরিটি গেট" স্ক্রিন দেখায় —
  `Initializing Security System… → Checking Network Connection… → Verifying Application Integrity… → Connecting to RHK Server… → Loading Community…`
  তারপর সফল হলে সাইটটা full-screen WebView-এ খোলে; ব্যর্থ হলে "SECURE PAGE UNAVAILABLE / TRY AGAIN"।
- স্ক্রিনে লেখা: `RHK ACCESS GATE`, `RHK / SECURE ACCESS GATE`, `RHK TRADING COMMUNITY`, `V1.0.0`।
- "Integrity check" বলতে আসলে শুধু ৪টা হালকা জিনিস দেখে: HTTPS কি না, হোস্ট allowlist-এ আছে কি না, কোডে secret আছে কি না (hardcoded `true`), আর release build কি না। এটা কোনো আসল tamper-detection নয়।

### WebView সেটিংস (বেশ ভালোভাবে tightened)
`javaScriptEnabled=true`, `domStorageEnabled=true`, `sharedCookiesEnabled=true`, কিন্তু
`thirdPartyCookiesEnabled=false`, `mixedContentMode='never'` (HTTP ব্লক), `allowFileAccess=false`, `allowUniversalAccessFromFileURLs=false`, `allowFileAccessFromFileURLs=false`, `webviewDebuggingEnabled=false`।
`usesCleartextTraffic="false"`, `allowBackup="false"`, `debuggable` নেই — এগুলো ঠিক আছে।

---

## ৩. Expo / Manus মেটাডেটা (`assets/app.config`)

```json
{
  "name": "RHK COMMUNITY", "slug": "rhktrade", "version": "1.0.0",
  "owner": "hjiiyygggff",
  "apiBaseUrl": "https://rhktrade-wchcsbxv.manus.space",
  "oauthPortalUrl": "https://manus.im",
  "oauthServerUrl": "https://api.manus.ai",
  "appId": "WChcSBxVAfsmAVtcQRvsmP",
  "eas.projectId": "964dcb3a-e275-49e7-83b1-8439ce489a4d",
  "scheme": "manus060868234445631"
}
```
অর্থাৎ অ্যাপটা **Manus** প্ল্যাটফর্মে জেনারেট হয়েছে, ব্র্যান্ড/কনটেন্ট "RHK Trading Community"-র, আর আসল লাইভ কনটেন্ট থাকে `hasib-one-fire.top` ডোমেইনে (shared hosting-এর `.top` ডোমেইন + PHP ফাইল)। Expo/EAS আপডেট চালু নেই (`expo.modules.updates.ENABLED=false`), তাই রিমোট থেকে কোড বদলানোর সুযোগ নেই।

---

## ৪. পারমিশন ও কম্পোনেন্ট

- INTERNET, ACCESS_NETWORK_STATE, WAKE_LOCK, POST_NOTIFICATIONS, RECEIVE_BOOT_COMPLETED, MODIFY_AUDIO_SETTINGS, USE_BIOMETRIC/USE_FINGERPRINT + Firebase push (FCM)।
- স্টোরেজ, SYSTEM_ALERT_WINDOW, VIBRATE ইত্যাদি `blockedPermissions`-এ ব্লক করা।
- কোনো Camera/Mic/Location/SMS/Contacts পারমিশন **নেই**।
- শুধু ১টা exported component: `MainActivity` (LAUNCHER + deep link scheme `manus060868234445631`)। বাকি সব Firebase/expo/startup provider-receiver `exported=false` বা নিজস্ব permission দিয়ে সুরক্ষিত।
- **FLAG_SECURE / screenshot ব্লক নেই** — তাই ট্রেডিং/অ্যাকাউন্ট স্ক্রিনের screenshot নেওয়া যাবে।

---

## ৫. ঝুঁকি মূল্যায়ন

| # | পর্যবেক্ষণ | সিভিয়ারিটি | ব্যাখ্যা |
|---|---|---|---|
| 1 | **সব লজিক/লগইন একটা PHP সাইটে WebView-এ** | ⚠️ উচ্চ | অ্যাপের ভিতরে কোনো কোড না থাকায় নিরাপত্তা সম্পূর্ণভাবে `hasib-one-fire.top` সার্ভারের উপর নির্ভরশীল। PHP/Plesk-জাতীয় সাইটে SQLi/XSS/admin panel দুর্বলতা থাকলে সরাসরি ইউজার অ্যাকাউন্ট ও (রিটেইল FX/ট্রেডিং হলে) টাকা ঝুঁকিতে। |
| 2 | **"Security gate" নাটকীয় কিন্তু আসলে দুর্বল** | মধ্যম | Integrity check শুধু কোডের ভেতরের ধ্রুবক, আসল APK signature verification বা Play Integrity নেই। ইউজারকে "secured" ভাব দেখানোর মার্কেটিং, প্রযুক্তিগত সুরক্ষা নয়। |
| 3 | **রিপ্যাকে করা APK** | মধ্যম | `CN=Manus App` self-signed সার্টিফিকেট, v1 সিগনেচার নেই, host allowlist থেকে বোঝা যায় সাইটটা পরে বসানো হয়েছে (`manus.space` নয়, `hasib-one-fire.top`)। Play Store-এ যায়নি — direct distribution। |
| 4 | ডোমেইন `.top` + shared hosting | মধ্যম | যেকোনো সময় ownership/expiry বদলাতে পারে; সার্টিফিকেট pinning নেই, তাই DNS/hosting compromise হলে অ্যাপই attacker-এর পেজ লোড করবে। |
| 5 | `sharedCookiesEnabled=true` | নিম্ন | WebView cookie Android-এর global cookie jar-এ যায়; অন্য কোনো app-এর WebView কো-ব্রাউজিং হলে থিওরেটিক্যালি ঝুঁকি। |
| 6 | FLAG_SECURE নেই | নিম্ন | স্ক্রিনশট/screen-record দিয়ে সংবেদনশীল ডেটা ফাঁস হতে পারে। |
| 7 | Firebase config | নিম্ন | `google_app_id` আছে কিন্তু বাইরে-readable `google-services` API key bundle-এ নেই; কোনো Stripe/private key/`AIza…` সিক্রেট পাওয়া যায়নি। |
| 8 | `targetSdk 36`, `debuggable=false`, cleartext বন্ধ, backup বন্ধ | ✅ ভালো | আধুনিক বেসলাইন ঠিক আছে। |

**Suspicious API স্ক্যান:** `SmsManager/sendTextMessage`, `Runtime.exec`, `DevicePolicyManager` — কিছুই নেই। `DexClassLoader` ও `AccessibilityService` স্ট্রিং শুধু AndroidX/Firebase লাইব্রেরির ভিতরে, অ্যাপের নিজের কোডে ব্যবহার নেই। **কোনো ম্যালওয়্যার-লক্ষণ (SMS Trojan, dropper, spy) পাওয়া যায়নি।** কোনো sensitive permission-ও চাওয়া হয়নি।

---

## ৬. উপসংহার

> **এটি ম্যালওয়্যার নয়** — একটা সাধারণ Expo WebView-অ্যাপ যা `https://hasib-one-fire.top/mahim-user.php` সাইটকে "RHK Trading Community" ব্র্যান্ডে Android অ্যাপ হিসেবে দেখায়।
>
> মূল ঝুঁকি অ্যাপের কোডে নয়, **সাইটটার উপর**: ইউজার/পাসওয়ার্ড, ব্যালেন্স বা লেনদেন যদি ওই PHP সাইটে হয়, তাহলে সেই সার্ভারের নিরাপত্তা, DNS, আর সার্টিফিকেটের উপর সবকিছু নির্ভর করছে — এবং ওই দিকটা এই APK থেকে যাচাই করা সম্ভব নয়। প্লাস, "Trading Community" নামে self-signed, Play Store-বহির্ভূত অ্যাপে আসল টাকা জমা দেওয়ার আগে খুব সতর্ক থাকা উচিত।

### ব্যবহারকারীর জন্য করণীয়
1. `hasib-one-fire.top` কে বিশ্বাস করার আগে WHOIS, TLS সার্টিফিকেট ও সাইটের ট্রাস্ট-হিস্ট্রি যাচাই করুন।
2. অ্যাপে **একই পাসওয়ার্ড রিইউজ করবেন না**; সম্ভব হলে আলাদা ইমেইল/পাসওয়ার্ড।
3. কোনো লেনদেন/ডিপোজিটের আগে টাকা ফেরত পাওয়ার নিশ্চয়তা (লাইসেন্স, রেগুলেশন) যাচাই করুন।
4. ট্রেডিং/ব্যালেন্স স্ক্রিনের স্ক্রিনশট পাবলিক টেলিগ্রাম/FB গ্রুপে শেয়ার করবেন না (FLAG_SECURE নেই)।

### ডেভেলপারের জন্য (যদি এটা আপনার অ্যাপ হয়)
- অ্যাপের UI/logic ভেতরে আনুন বা অন্তত pinned certificate + short-lived token ব্যবহার করুন; `hasib-one-fire.top`-এ HTTPS+HSTS নিশ্চিত করুন।
- `FLAG_SECURE` যোগ করুন সংবেদনশীল স্ক্রিনে; `sharedCookiesEnabled` দরকার না হলে বন্ধ করুন।
- Play Integrity API + আসল APK signature hash check দিয়ে "integrity gate" কে অর্থবহ করুন, নাহলে ওই স্ক্রিন শুধু ভুয়া assurance দিচ্ছে।
- PHP ব্যাকএন্ড হলে SQLi/XSS/session fixation ও admin panel exposure পেন্টেস্ট করান।

---

### রেফারেন্স — বিশ্লেষণে ব্যবহৃত আর্টিফ্যাক্ট
- `base.apk` → `AndroidManifest.xml` (ডিকোডেড), `assets/app.config`, `assets/index.android.bundle` (Hermes, hbc-decompiler দিয়ে decompiled), `resources.arsc`, `classes*.dex`
- মূল 7z এবং APK অপরিবর্তিত রাখা হয়েছে; কোনো ফাইল mod করা হয়নি।
