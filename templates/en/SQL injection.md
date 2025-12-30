# 【1】【2】【3】【7】 SQL injection

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

- SQL injection

## Root Cause

- A SQL injection vulnerability was found in the '【7】' file of the '【4】' project. The reason for this issue is that attackers inject malicious code from the parameter '【9】' and use it directly in SQL queries without the need for appropriate cleaning or validation. This allows attackers to forge input values, thereby manipulating SQL queries and performing unauthorized operations.

## Impact

- Attackers can exploit this SQL injection vulnerability to achieve unauthorized database access, sensitive data leakage, data tampering, comprehensive system control, and even service interruption, posing a serious threat to system security and business continuity.

# DESCRIPTION

- During the security review of "【4】",I discovered a critical SQL injection vulnerability in the "【4】" file. This vulnerability stems from insufficient user input validation of the '【9】‘ parameter, allowing attackers to inject malicious SQL queries. Therefore, attackers can gain unauthorized access to databases, modify or delete data, and access sensitive information. Immediate remedial measures are needed to ensure system security and protect data integrity.

# 【14】

# Vulnerability details and POC

## Vulnerability lonameion:

- '【9】' parameter

## Payload:

```makefile
---

【10】

---
```

## The following are screenshots of some specific information obtained from testing and running with the sqlmap tool:

```bash
【12】
```

【13】
【13】
【13】

# Suggested repair

1. **Use prepared statements and parameter binding:**
   Preparing statements can prevent SQL injection as they separate SQL code from user input data. When using prepare statements, the value entered by the user is treated as pure data and will not be interpreted as SQL code.

2. **Input validation and filtering:**
   Strictly validate and filter user input data to ensure it conforms to the expected format.

3. **Minimize database user permissions:**
   Ensure that the account used to connect to the database has the minimum necessary permissions. Avoid using accounts with advanced permissions (such as' root 'or' admin ') for daily operations.

4. **Regular security audits:**
   Regularly conduct code and system security audits to promptly identify and fix potential security vulnerabilities.
