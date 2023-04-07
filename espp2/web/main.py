#!/usr/bin/env python3

'''
ESPP2 web server
'''
# pylint: disable=invalid-name

import logging
from typing import Optional
from os.path import realpath
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import parse_obj_as
from fastapi.staticfiles import StaticFiles
from espp2.main import do_taxes, do_holdings_1, do_holdings_2
from espp2.datamodels import ESPPResponse, Wires, Holdings, ExpectedBalance
from espp2.positions import Positions
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/holdings_1/", response_model=Holdings)
async def generate_holdings_1(
        transaction_files: list[UploadFile],
        broker: str = Form(...),
        holdfile: UploadFile | None = None,
        opening_balance: str = Form(...),
        year: int = Form(...)):
    '''Generate previous year holdings from a plethora of transaction files'''
    opening_balance = None

    if opening_balance:
        opening_balance = json.loads(opening_balance)
        opening_balance = parse_obj_as(Holdings, opening_balance)

    if holdfile and holdfile.filename == '':
        holdfile = None
    elif holdfile:
        holdfile = holdfile.file
    try:
        holdings = do_holdings_1(
            broker, transaction_files, holdfile, year, opening_balance=opening_balance)
        if type(holdings) == list:
            p = Positions(year - 1, holdings, [], received_wires=Wires(__root__=[]))
            p.process()
            holdings = p.holdings(year - 1, broker)
        return holdings
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/holdings_2/", response_model=Holdings)
async def generate_holdings_2(
        transaction_files: list[UploadFile],
        broker: str = Form(...),
        year: int = Form(...),
        expected_balance: str = Form(...)):
    '''Generate holdings from complete purchase history from stocks web site'''
    if expected_balance:
        expected_balance = json.loads(expected_balance)
        expected_balance = parse_obj_as(ExpectedBalance, expected_balance)
    try:
        holdings = do_holdings_2(broker, transaction_files, year, expected_balance=expected_balance)
        if type(holdings) == list:
            p = Positions(year - 1, holdings, [], received_wires=Wires(__root__=[]))
            p.process()
            holdings = p.holdings(year - 1, broker)
        return holdings
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/taxreport/", response_model=ESPPResponse)
async def taxreport(
        transaction_file: UploadFile,
        broker: str = Form(...),
        holdfile: UploadFile | None = None,
        wires: str = Form(""),
#        opening_balance: str = Form(...),
        year: int = Form(...)):
    '''File upload endpoint'''
    opening_balance = None
    if wires:
        wires_list = json.loads(wires)
        wires = Wires(__root__=wires_list)

    if opening_balance:
        opening_balance = json.loads(opening_balance)
        opening_balance = parse_obj_as(Holdings, opening_balance)

    if holdfile and holdfile.filename == '':
        holdfile = None
    elif holdfile:
        holdfile = holdfile.file
    try:
        report, holdings, summary = do_taxes(
            broker, transaction_file, holdfile, wires, year)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ESPPResponse(tax_report=report, holdings=holdings, summary=summary)


app.mount("/", StaticFiles(directory=realpath(
    f'{realpath(__file__)}/../public'), html=True), name='public')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
