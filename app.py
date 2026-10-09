from flask import Flask, render_template, request, redirect, url_for, flash
from pathlib import Path
from datetime import datetime
import json, os, re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pgmate-local-demo-key')
BASE = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('PGMATE_DATA_DIR', BASE / 'data'))
FILES = {name: DATA_DIR / f'{name}.json' for name in ('members', 'expenses', 'complaints')}

def ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in FILES.values():
        if not path.exists(): path.write_text('[]', encoding='utf-8')

def read_records(kind):
    ensure_files()
    try:
        data = json.loads(FILES[kind].read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def save_records(kind, records):
    ensure_files()
    tmp = FILES[kind].with_suffix('.json.tmp')
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(FILES[kind])

def new_id(records): return max((int(x.get('id', 0)) for x in records), default=0) + 1
def clean(key): return (request.form.get(key) or '').strip()
def valid_contact(value): return bool(re.fullmatch(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|[0-9+()\-\s]{7,20}', value))

@app.context_processor
def common(): return {'year': datetime.now().year}

@app.get('/')
def dashboard():
    members, expenses, complaints = (read_records(k) for k in ('members','expenses','complaints'))
    month = datetime.now().strftime('%Y-%m')
    current = [e for e in expenses if e.get('date','').startswith(month)]
    total = sum(float(e.get('amount', 0)) for e in current)
    categories = {}
    for e in current: categories[e.get('category','Other')] = categories.get(e.get('category','Other'), 0) + float(e.get('amount',0))
    pending = sum(c.get('status') != 'Resolved' for c in complaints)
    score = max(0, 100 - pending * 8 - (10 if not total else 0))
    return render_template('index.html', members=members, expenses=current, total=total, categories=categories,
                           pending=pending, resolved=len(complaints)-pending, score=score,
                           highest=max(categories, key=categories.get) if categories else 'No expenses yet')

@app.route('/members', methods=['GET','POST'])
def members_page():
    members = read_records('members')
    if request.method == 'POST':
        name, room, contact = clean('name'), clean('room'), clean('contact')
        if not name or not room or not valid_contact(contact):
            flash('Enter a name, room, and valid phone number or email.', 'error')
        else:
            members.append({'id':new_id(members),'name':name,'room':room,'contact':contact})
            save_records('members', members); flash('Member added successfully.', 'success')
        return redirect(url_for('members_page'))
    return render_template('members.html', members=members)

@app.post('/members/<int:item_id>/delete')
def delete_member(item_id):
    data=read_records('members'); updated=[x for x in data if int(x.get('id',0)) != item_id]
    save_records('members',updated); flash('Member removed.' if len(data)!=len(updated) else 'Member not found.','success')
    return redirect(url_for('members_page'))

@app.route('/expenses', methods=['GET','POST'])
def expenses_page():
    expenses, members = read_records('expenses'), read_records('members')
    if request.method == 'POST':
        try:
            amount=round(float(clean('amount')),2)
            if amount <= 0: raise ValueError
        except ValueError:
            flash('Enter an amount greater than zero.', 'error'); return redirect(url_for('expenses_page'))
        title, category, paid_by, date = clean('title'), clean('category'), clean('paid_by'), clean('date') or datetime.now().strftime('%Y-%m-%d')
        if not title or not category or not paid_by:
            flash('Complete all required fields.', 'error'); return redirect(url_for('expenses_page'))
        expenses.append({'id':new_id(expenses),'title':title,'category':category,'amount':amount,'paid_by':paid_by,'date':date})
        save_records('expenses',expenses); flash('Expense recorded.', 'success'); return redirect(url_for('expenses_page'))
    expenses.sort(key=lambda x:(x.get('date',''),int(x.get('id',0))),reverse=True)
    return render_template('expenses.html', expenses=expenses, members=members, today=datetime.now().strftime('%Y-%m-%d'))

@app.post('/expenses/<int:item_id>/delete')
def delete_expense(item_id):
    data=read_records('expenses'); updated=[x for x in data if int(x.get('id',0)) != item_id]
    save_records('expenses',updated); flash('Expense removed.' if len(data)!=len(updated) else 'Expense not found.','success')
    return redirect(url_for('expenses_page'))

@app.get('/split')
def split_page():
    members, expenses=read_records('members'), read_records('expenses')
    total=sum(float(e.get('amount',0)) for e in expenses); share=total/len(members) if members else 0
    paid={m['name']:0.0 for m in members}
    for e in expenses:
        if e.get('paid_by') in paid: paid[e['paid_by']]+=float(e.get('amount',0))
    balances=[{'name':n,'paid':v,'balance':round(v-share,2)} for n,v in paid.items()]
    return render_template('split.html', total=total, share=share, balances=balances, count=len(members))

@app.route('/complaints', methods=['GET','POST'])
def complaints_page():
    complaints, members=read_records('complaints'), read_records('members')
    if request.method == 'POST':
        title, desc, reporter, priority=clean('title'),clean('description'),clean('reported_by'),clean('priority')
        if not title or not desc or not reporter or priority not in {'Low','Medium','High'}:
            flash('Complete all complaint fields.','error')
        else:
            complaints.append({'id':new_id(complaints),'title':title,'description':desc,'reported_by':reporter,
                               'priority':priority,'status':'Pending','created_at':datetime.now().strftime('%Y-%m-%d %H:%M')})
            save_records('complaints',complaints); flash('Complaint submitted.','success')
        return redirect(url_for('complaints_page'))
    complaints.sort(key=lambda c:(c.get('status')=='Resolved', c.get('priority')!='High', int(c.get('id',0))))
    return render_template('complaints.html', complaints=complaints, members=members)

@app.post('/complaints/<int:item_id>/status')
def complaint_status(item_id):
    status=clean('status')
    if status not in {'Pending','In Progress','Resolved'}:
        flash('Invalid status.','error'); return redirect(url_for('complaints_page'))
    data=read_records('complaints'); found=False
    for c in data:
        if int(c.get('id',0))==item_id: c['status']=status; found=True; break
    save_records('complaints',data); flash('Complaint updated.' if found else 'Complaint not found.','success' if found else 'error')
    return redirect(url_for('complaints_page'))

@app.get('/reports')
def reports():
    expenses=read_records('expenses'); cats={}; months={}
    for e in expenses:
        amount=float(e.get('amount',0)); cat=e.get('category','Other'); month=e.get('date','')[:7] or 'Unknown'
        cats[cat]=cats.get(cat,0)+amount; months[month]=months.get(month,0)+amount
    return render_template('reports.html', categories=cats, months=dict(sorted(months.items())),
                           total=sum(float(e.get('amount',0)) for e in expenses), count=len(expenses))

@app.errorhandler(404)
def missing(_): return render_template('error.html', code=404, message='Page not found.'),404

ensure_files()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=os.environ.get('FLASK_DEBUG')=='1')
