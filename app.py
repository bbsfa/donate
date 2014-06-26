from flask import Flask, render_template, request, redirect, url_for
from flask.ext.pymongo import PyMongo
from bson.objectid import ObjectId
import urllib
import datetime

app = Flask('bbsDonate')
mongo = PyMongo()
mongo.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/donate_notify', methods=['POST', 'GET'])
def donate_notify():
    mongo.db.ipn.insert({
      'item_number': request.form.get('item_number', None),
      'payment_status': request.form.get('payment_status', None)
    })
    donation = mongo.db.donations.find_one({'_id': ObjectId(request.form['item_number'])})
    if donation:
        payment_status = request.form['payment_status']
        mongo.db.donations.update({ '_id': donation['_id']}, { '$set': { 'payment_status': payment_status }})
        return 'ok'
    return 'err'


@app.route('/donate', methods=['POST'])
def donate():

    is_anonymous = request.form.get('anonymous', False)

    if not is_anonymous:
        # Try and parse out a first and last name
        name_parts = request.form.get('name', '').split(' ')
        first_name = name_parts[0]
        last_name  = name_parts[-1]
    else:
        first_name = 'Anonymous'
        last_name  = 'Donor'

    try:
        amount = request.form.get('amount', None)
        if amount == 'other':
            amount = request.form.get('other_amount', None)
        if not amount:
            amount = 25
        amount = float(amount)
    except:
        amount = 25

    # Put them in MailChimp (Donors List).
    if not is_anonymous:
        from mailchimp import Mailchimp, Lists
        mailchimp = Mailchimp('374952867b477cf38a8f8cef6faabe23-us3')
        lists = Lists(mailchimp)
        merge_vars = {
            'FNAME': first_name,
            'LNAME': last_name
        }
        lists.subscribe('cd75a9fd9c', {'email': request.form['email'] }, merge_vars,
                double_optin=False, update_existing=True)

    # Build PayPal request.
    url    = 'https://www.paypal.com/cgi-bin/webscr'
    notify_url = 'http://' + request.host + url_for('donate_notify')
    params = {
        'created_at': datetime.datetime.utcnow(),
        'business': 'T2QEATDJB5YWY',
        'cmd': '_donations',
        'item_name': 'Bardet Biedl Syndrome Fund',
        'amount': amount,
        'notify_url': notify_url,
        'payment_status': None
    }

    if not is_anonymous:
        params['first_name'] = first_name
        params['last_name'] = last_name
        params['email'] = request.form['email']

    # Save to Mongo
    mongo.db.donations.insert(params)
    params['item_number'] = str(params.pop('_id'))
    params.pop('payment_status')
    params.pop('created_at')
    return redirect(url + '?' + urllib.urlencode(params))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
