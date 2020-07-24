import os
import json
import requests
import atexit
from lib import electrum_lib
from lib import electrums
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)


electrum_urls = {}
explorers_urls = {}

@app.before_first_request
def restore_data_from_backup():
    global electrum_urls
    electrum_urls = electrum_lib.restore_electrums_from_backup()
    global explorers_urls
    explorers_urls = electrum_lib.restore_explorers_from_backup()


@app.route("/")
def main():
    global electrum_urls
    return render_template('index.html', electrum_urls=electrum_urls)


@app.route("/atomicdex-mobile")
def filter_mobile():
    global electrum_urls
    return render_template('atomicdex.html', electrum_urls=electrum_urls)


@app.route("/explorers")
def explorers():
    global explorers_urls
    return render_template('explorers.html', explorers_urls=explorers_urls)


@app.route("/api")
def api():
    return render_template('api-docs.html')


### API CALLS

@app.route('/api/electrums')
def get_all_electrums():
    global electrum_urls
    return jsonify(electrum_urls)


@app.route('/api/atomicdex-mob')
def get_only_atomicdex_mobile_electrums():
    global electrum_urls
    d = {}
    for coin, urls in electrum_urls.items():
        if coin in electrums.atomic_dex_mobile:
            d[coin] = urls
    return jsonify(d)


@app.route('/api/explorers')
def get_all_explorers():
    global explorers_urls
    return jsonify(explorers_urls)



### BACKGROUND JOBS

def gather_and_backup_electrums():
    app.logger.info('started background job: electrums update')
    global electrum_urls
    electrum_urls = electrum_lib.call_electrums_and_update_status(electrum_urls, electrums.electrum_version_call, electrums.eth_call)
    electrum_lib.backup_electrums(electrum_urls)
    app.logger.info('finished background job: electrums update and backup')

def gather_and_backup_explorers():
    app.logger.info('started background job: explorers update')
    global explorers_urls
    explorers_urls = electrum_lib.call_explorers_and_update_status(explorers_urls)
    electrum_lib.backup_explorers(explorers_urls)
    app.logger.info('finished background job: explorers update and backup')

def init_electrum_repo_links():
    repo_links = electrum_lib.combine_electrums_repo_links(electrums.all_tickers, electrums.link, electrums.eth_link)

    d, c = electrum_lib.gather_tcp_electrumx_links_into_dict(repo_links)
    app.logger.info('finished background job: parse electrum urls')
    global electrum_urls
    electrum_urls = d
    electrum_lib.backup_electrums(electrum_urls)
    electrum_urls = electrum_lib.call_electrums_and_update_status(electrum_urls, electrums.electrum_version_call, electrums.eth_call)
    electrum_lib.backup_electrums(electrum_urls)


scheduler = BackgroundScheduler()
# run electrum servers check after web server is started
scheduler.add_job(func=init_electrum_repo_links, run_date = datetime.now() + timedelta(seconds = 10))
scheduler.add_job(func=gather_and_backup_electrums, trigger="interval", seconds=500)
#scheduler.add_job(func=gather_and_backup_explorers, trigger="interval", seconds=100)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)