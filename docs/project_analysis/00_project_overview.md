# Project Overview

## 1. What this project is

This project is a Vietnamese stock co-movement and clustering system.  
Its goal is to identify groups of stocks that behave similarly over time, mainly based on market time-series data such as price, return, volume, and derived features.

The project is not designed as an automatic trading bot.  
It does not directly make buy/sell decisions.  
Instead, it provides analytical outputs that help users understand market structure, stock similarity, cluster changes, and possible relationships between stocks.

## 2. Main problem

Given a universe of Vietnamese stocks, the system answers questions such as:

- Which stocks move similarly over a recent time window?
- Which stocks belong to the same behavioral cluster?
- How stable are these clusters over time?
- Which stocks recently changed clusters?
- What market or news context may explain a cluster movement?

## 3. Main inputs

The system uses:

- Market numerical data:
  - OHLCV
  - benchmark data
  - price history
  - return series
  - volume/liquidity information

- Optional news data:
  - article title
  - article content
  - source
  - published time
  - related tickers
  - summary or sentiment features

- Optional RAG/retrieval data:
  - not part of the core clustering pipeline yet
  - may be used later for explanation and question-answering

## 4. Main outputs

The system produces:

- stock clusters
- cluster membership per run
- cluster history per ticker
- cluster quality metrics
- similarity graph
- cluster-level summaries
- stock profile pages
- optional news context per ticker or cluster

## 5. What the project does not do

This project does not currently focus on:

- automatic trading execution
- portfolio optimization
- agent-based investment committee decisions
- direct buy/sell recommendation
- real-time high-frequency trading
- financial report OCR pipeline

## 6. Expected usage

The system is intended to run as a daily batch analytics pipeline.  
After market data is collected, the clustering pipeline computes new stock groups and stores the result.  
The dashboard then reads the stored results and presents them to users.