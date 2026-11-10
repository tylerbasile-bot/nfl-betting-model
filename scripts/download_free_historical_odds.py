#!/usr/bin/env python3
"""Fetch free-tier EndzoneAPI per-book historical opening/closing data to Drive.

Manual Colab execution only. 2 requests per season at 10 credits each.
Never place API keys in URLs, repositories, data files or logs.
DOES NOT TOUCH Model 13 frozen prospective forecasts.
"""
import argparse
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

BASE="https://mcp.endzoneapi.com/v1/get_odds"

def run(api_key,season,outdir,dry_run=False):
    if not api_key and not dry_run:
        raise ValueError("ENDZONEAPI_API_KEY is missing")
    outdir=Path(outdir)
    for typ in ("opening","closing"):
        path=outdir/f"endzone_{season}_{typ}.json"
        if path.exists():
            print(f"Already saved: {path}; skipping paid-credit request")
            continue
        body={"season":int(season),"snapshot_type":typ,"limit":500}
        if dry_run:
            print("Dry-run, 0 credits:",body)
            continue
        payload=json.dumps(body).encode("utf-8")
        request=Request(BASE,data=payload,method="POST",headers={
            "Content-Type":"application/json","x-api-key":api_key,
            "User-Agent":"NFL-free-historical-research/1.0"})
        try:
            with urlopen(request,timeout=55) as resp:
                result=json.loads(resp.read(8_000_001).decode("utf-8"))
        except (HTTPError,URLError,TimeoutError,ValueError) as exc:
            raise RuntimeError(
                f"Historical query unavailable for {season} {typ}: {type(exc).__name__}"
            ) from None
        if not isinstance(result,(list,dict)):
            raise RuntimeError(f"Unexpected response type for {season} {typ}")
        # Preserve the provider's original response and metadata for audit.
        outdir.mkdir(parents=True,exist_ok=True)
        wrapper={"source":"endzoneapi","retrieved_utc":datetime.now(timezone.utc).isoformat(),
                 "query":body,"payload":result}
        path.write_text(json.dumps(wrapper,indent=2),encoding="utf-8")
        print(f"Saved {season} {typ} provider response to {path}")
    print("Note: a provider opening/closing capture is NOT necessarily a sportsbook's true opener/close.")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--years",type=int,nargs="+",default=[2022,2023,2024,2025])
    parser.add_argument("--output-dir",default="/content/drive/MyDrive/NFL_Betting_Data/free_historical_odds")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    key=os.environ.get("ENDZONEAPI_API_KEY","")
    if not key and not args.dry_run:
        from getpass import getpass
        key=getpass("Paste your FREE EndzoneAPI key (hidden): ")
    plans=sum(not (Path(args.output_dir)/f"endzone_{year}_{typ}.json").exists()
              for year in args.years for typ in ("opening","closing"))
    print(f"Planned queries: {plans}. Estimated free-tier credit consumption: {plans*10}.")
    if plans*10>500:
        raise SystemExit("Refusing >500 estimated credits.")
    for year in args.years:
        run(key,year,args.output_dir,args.dry_run)

if __name__=="__main__":
    main()
