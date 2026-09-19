# Wallet Recovery System

A multi-user Flask web application designed to identify recoverable value from digital wallets and provide structured recovery and wallet-consolidation workflows.

The system allows users to register, log in securely, manage their own wallets, identify recoverable surplus, add funds, request recovery, retrieve trapped value during wallet exit, and review wallet and recovery transaction history.

> **Project Note:**
> This project is an application-level simulation of wallet recovery and consolidation workflows. It does not claim direct integration with or permission from real third-party wallet providers.



## Overview

Digital wallets and prepaid-style accounts can contain balances that are difficult to use or withdraw because of minimum-balance requirements or account-exit conditions.

The Wallet Recovery System models this problem by allowing users to:

1. Add and manage multiple wallets.
2. Define each wallet's current balance and minimum required balance.
3. Calculate the amount available above the minimum balance.
4. Recover available surplus through supported recovery options.
5. Mark a wallet for exit or consolidation.
6. Retrieve the remaining balance during the wallet exit process.
7. Track all wallet and recovery activities.

The application is designed as a modular Flask project with separate authentication, wallet, recovery, service, template, and testing components.

---

## Problem Statement

Users may maintain balances across multiple digital wallets.

In some situations:

- A wallet may require a minimum balance.
- A portion of the balance may remain unused.
- Users may want to recover surplus value.
- Users may eventually want to leave or consolidate a wallet.
- It can be difficult to track the value recovered from multiple wallets manually.

The project addresses this problem by providing a centralized application that tracks wallets and calculates recoverable value based on user-defined wallet rules.

---

## Objectives

The main objectives of the system are:

- Provide secure multi-user registration and login.
- Allow users to manage their own wallets.
- Calculate recoverable wallet surplus.
- Prevent normal recovery from reducing a wallet below its minimum balance.
- Support wallet exit/consolidation workflows.
- Record wallet and recovery transactions.
- Maintain user-specific data isolation.
- Provide a clean dashboard for monitoring wallet recovery activity.

---

## Key Features

### User Authentication

- User registration
- Email validation
- Secure password hashing
- Login and logout
- Session-based authentication
- Protected application routes
- User-specific profile information

### Wallet Management

Users can:

- Add wallets
- Specify a wallet provider
- Set the current balance
- Set the minimum balance
- Add money to active wallets
- Request wallet exit/consolidation
- Resume a wallet that is awaiting exit
- View wallet activity

### Wallet Analysis

The system provides:

- Current balance
- Minimum balance
- Recoverable surplus
- Recovered value
- Remaining recoverable value
- Potentially trapped value
- Wallet status

### Recovery

The application supports:

- Surplus recovery
- Reward Credits
- Voucher
- Wallet Consolidation
- Exit recovery for wallets marked for exit

### Transaction Tracking

The application maintains:

- Wallet transaction history
- Recovery transaction history
- Recovery reference codes
- Transaction type
- Amount
- Balance after transaction
- Description
- Date and time

### User Data Isolation

Each user can access only their own:

- Profile
- Wallets
- Wallet transactions
- Recovery transactions
- Recovery data

---

## How the System Works

The general workflow is:

User Registration
       ↓
User Login
       ↓
Dashboard
       ↓
Add Wallet
       ↓
Set Balance + Minimum Balance
       ↓
Calculate Recoverable Value
       ↓
 ┌──────────────────────────┐
 │                          │
 ↓                          ↓
Recover Surplus        Request Wallet Exit
 │                          │
 ↓                          ↓
Keep Minimum Balance   Retrieve Trapped Value
 │                          │
 ↓                          ↓
Recovery Transaction   Wallet Closed
 │
 ↓
Recovery History
