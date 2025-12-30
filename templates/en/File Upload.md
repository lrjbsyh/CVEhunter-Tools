# 【1】【2】【3】【7】Unrestricted Upload

# NAME OF AFFECTED PRODUCT(S)

- 【4】

## Vendor Homepage

- 【5】

# AFFECTED AND/OR FIXED VERSION(S)

## Submitter

- 【6】

## Vulnerable File

- 【7】

## VERSION(S)

- 【3】

## Software Link

- 【8】

# PROBLEM TYPE

## Vulnerability Type

- Unrestricted Upload

## Root Cause

- A file unrestricted upload was found in the '【7】' file of the '【4】' project. The reason for this issue is that the system does not properly validate the type, format, or content of uploaded files. Attackers can upload malicious files (such as PHP scripts) by bypassing simple checks (e.g., only verifying file extensions without MIME type validation or content inspection), which are then executed on the server.

## Impact

- Attackers can exploit this file upload vulnerability to upload malicious scripts, gain server-side code execution privileges, access or modify sensitive data, take full control of the server, or spread malware, posing a severe threat to system security and data confidentiality.

# DESCRIPTION

- During the security review of "【4】", I discovered a critical file upload vulnerability in the "【7】" file. This vulnerability arises due to inadequate validation of the 'file' parameter used for uploading files. Attackers can bypass the system's weak checks (e.g., changing malicious file extensions to allowed types) and upload executable scripts, leading to unauthorized server access. Immediate remedial measures are required to secure the system.

# 【14】

# Vulnerability details and POC

## Vulnerability location:

- 'file' parameter in /upload.php

## PoC:

```
---
【11】
---
```

## The following are screenshots of some specific information obtained from testing the file upload process:

```bash
# Example command to verify the uploaded malicious file
curl http://target.com/uploads/shell.php?cmd=whoami
```

【13】

# Suggested repair

1. **Strict file type validation:**
   
   - Validate file types using a combination of MIME type checks, file signature (magic number) verification, and allowed extension whitelisting (avoid blacklists, as they can be bypassed).
   - Reject files that do not match the expected type, even if their extension is allowed.

2. **Secure file storage:**
   
   - Store uploaded files in a directory outside the web root (if direct execution is not required) to prevent direct access.
   - Generate random filenames for uploaded files (instead of using the original name) to avoid path traversal and ensure uniqueness.

3. **Execute permission restrictions:**
   
   - Disable PHP execution permissions for the upload directory via server configurations (e.g., Apache .htaccess or Nginx config).

4. **Content inspection:**
   
   - Scan uploaded files for malicious content using antivirus software or dedicated security tools to detect hidden scripts.

5. **Input size limits:**
   
   - Restrict the maximum file size allowed for uploads to prevent large malicious files from consuming server resources.
   - Implement server-side validation to ensure that the file size does not exceed the allowed limit.

6. **Regular security audits:**
   
   - Conduct regular security audits and vulnerability assessments to identify and address new file upload vulnerabilities that may arise.
   - Stay updated with the latest security best practices and apply patches or updates as needed.