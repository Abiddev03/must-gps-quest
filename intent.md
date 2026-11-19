# Intent

## Problem
Advertisers pay by distance driven. The distance we report per vehicle per day is too high because the raw GPS data has problems: noisy pings (off-road jumps and impossible speeds), duplicate pings, and pings that arrive out of order. On the sample data, the reported distance was **374.079 km**, but the true distance is **216.090 km**.

## What I chose to fix
I chose **GPS noise** as the main problem, even though out-of-order pings add more distance on their own (+84.6 km vs +52.9 km). My reasons:

1. **The advertiser can see why.** The tool shows, ping by ping, why each one was removed (off-road or speed). That makes the number defensible to a paying customer.
2. **Noise detection needs a timestamp sort first**, so fixing noise also removes most of the out-of-order inflation.
3. **Out-of-order alone is a one-line sort.** Noise needs business rules and edge-case testing, which is where QA judgement matters.

## Out of scope
- The day boundary (UTC vs UTC+9). It moves 77.9 km to the wrong day, but it is a business decision, not a data bug. All acceptance numbers use UTC days.

## Acceptance criteria
- Distance after cleaning equals the expected **216.090 km** for the sample.
- All **133** noisy pings are removed, and **0** good pings are dropped.
- Duplicates (66) and out-of-order pings (120) are handled.
- Tests pass on the fixed code and fail on the old code.
