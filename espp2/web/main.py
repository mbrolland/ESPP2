#!/usr/bin/env python3

'''
ESPP2 web server
'''
# pylint: disable=invalid-name

import logging
import json
from typing import Optional
from os.path import realpath
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import TypeAdapter
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from espp2.main import (do_taxes, do_holdings_1, do_holdings_2,
                        do_holdings_3, do_holdings_4, preheat_cache, get_zipdata)
from espp2.datamodels import ESPPResponse, Wires, Holdings, ExpectedBalance

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/holdings_1/", response_model=Holdings)
async def generate_holdings_1(
        transaction_files: list[UploadFile],
        broker: str = Form(...),
        holdfile: UploadFile | None = None,
        # opening_balance: str = Form(...),
        year: int = Form(...)):
    '''Generate previous year holdings from a plethora of transaction files'''
    opening_balance = None

    if holdfile and holdfile.filename == '':
        holdfile = None
    elif holdfile:
        holdfile = holdfile.file
    try:
        return do_holdings_1(
            broker, transaction_files, holdfile, year, opening_balance=opening_balance)
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
        adapter = TypeAdapter(ExpectedBalance)
        expected_balance = adapter.validate_json(expected_balance)
    try:
        return do_holdings_2(broker, transaction_files, year, expected_balance=expected_balance)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/holdings_3/", response_model=Holdings)
async def generate_holdings_3(
        transaction_file: UploadFile,
        broker: str = Form(...),
        year: int = Form(...),
        expected_balance: str = Form()):
    '''
    Calculate a holdings based on an expected balance and a single transaction file.
    This will only work if any position prior to the beginngin of the transaction file has been
    sold before the tax year. This has only been tested with Schwab.
    '''
    adapter = TypeAdapter(ExpectedBalance)
    expected_balance = adapter.validate_json(expected_balance)
    try:
        return do_holdings_3(broker, transaction_file, year, expected_balance=expected_balance)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/holdings_4/", response_model=Holdings)
async def generate_holdings_4(
        transaction_file: UploadFile,
        broker: str = Form(...),
        year: int = Form(...)):
    '''
    Calculate holdings based on the Morgan HTML file.
    '''
    try:
        return do_holdings_4(broker, transaction_file, year)
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
        adapter = TypeAdapter(Holdings)
        opening_balance= adapter.validate_json(opening_balance)

    if holdfile and holdfile.filename == '':
        holdfile = None
    elif holdfile:
        holdfile = holdfile.file
    try:
        report, holdings, exceldata, summary = do_taxes(
            broker, transaction_file, holdfile, wires, year)
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    zipdata = get_zipdata([(f'espp-holdings-{year}.json', holdings),
                           (f'espp-portfolio-{year}.xlsx', exceldata)])
    return ESPPResponse(tax_report=report, zip=zipdata, summary=summary)


# This seems to keep us from caching the files too agressively.
# Is there a simpler way to do cache control serverside?
# Might require e.g. an nginx proxy?

@app.get('/bundle.js')
async def get_bundle():
    logger.debug('bundle.js')
    return FileResponse(
        realpath(f'{realpath(__file__)}/../public/bundle.js'),
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        })

app.mount("/", StaticFiles(directory=realpath(
    f'{realpath(__file__)}/../public'), html=True), name='public')

if __name__ == "__main__":
    preheat_cache()
    uvicorn.run(app, host="0.0.0.0", port=8000)
