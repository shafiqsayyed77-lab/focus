import urllib.request
import json

# 1. Login
login_data = json.dumps({'email': 'alex.student@focusflow.edu', 'password': 'Student123!'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req)
token = json.loads(res.read().decode('utf-8'))['token']
print('PASS: Login successful')

# 2. Check Static and Page Routes
for url in ['http://127.0.0.1:8000/ai', 'http://127.0.0.1:8000/dashboard', 'http://127.0.0.1:8000/static/js/dashboard.js', 'http://127.0.0.1:8000/static/css/style.css']:
    r = urllib.request.urlopen(url)
    print(f'PASS: {url} -> Status {r.status}, size {len(r.read())} bytes')

# 3. Test AI Study Plan
plan_req = urllib.request.Request(
    'http://127.0.0.1:8000/api/ai/study-plan',
    data=json.dumps({
        'subject': 'Computer Networks',
        'topics': 'IPv4, ARP, IPv6',
        'available_time': 60,
        'energy_level': 'Normal',
        'priority': 'High'
    }).encode('utf-8'),
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
)
plan_res = json.loads(urllib.request.urlopen(plan_req).read().decode('utf-8'))
print('PASS: Study Plan items:')
for item in plan_res['schedule']:
    print(f"   - {item['duration_label']} — {item['title']}")

# 4. Test AI Explain Topic
explain_req = urllib.request.Request(
    'http://127.0.0.1:8000/api/ai/explain',
    data=json.dumps({'topic': 'Address Resolution Protocol (ARP)', 'subject': 'Computer Networks'}).encode('utf-8'),
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
)
explain_res = json.loads(urllib.request.urlopen(explain_req).read().decode('utf-8'))
print('PASS: Explain Topic:', explain_res['topic'])
print('   Important points count:', len(explain_res['important_points']))
print('   Has example:', bool(explain_res['small_example']))

# 5. Test AI Quiz
quiz_req = urllib.request.Request(
    'http://127.0.0.1:8000/api/ai/quiz',
    data=json.dumps({'subject': 'Computer Networks', 'topic': 'IPv4', 'num_questions': 4}).encode('utf-8'),
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
)
quiz_res = json.loads(urllib.request.urlopen(quiz_req).read().decode('utf-8'))
print('PASS: Quiz generated:', len(quiz_res['questions']), 'questions, each with 4 options!')
for q in quiz_res['questions']:
    assert len(q['options']) == 4
    assert 0 <= q['correct_answer'] < 4
    assert len(q['explanation']) > 10
    print(f"   Q{q['id']}: {q['question'][:50]}... -> Correct: {q['options'][q['correct_answer']]}")

# 6. Verify existing Dashboard and Tasks APIs are intact
dash_req = urllib.request.Request('http://127.0.0.1:8000/api/dashboard/stats', headers={'Authorization': 'Bearer ' + token})
dash_res = json.loads(urllib.request.urlopen(dash_req).read().decode('utf-8'))
print('PASS: Dashboard stats intact. Study time:', dash_res['stats']['study_time_today'], 'Streak:', dash_res['stats']['streak'])

tasks_req = urllib.request.Request('http://127.0.0.1:8000/api/tasks', headers={'Authorization': 'Bearer ' + token})
tasks_res = json.loads(urllib.request.urlopen(tasks_req).read().decode('utf-8'))
print('PASS: Tasks list intact. Count:', tasks_res['count'])

print('\nALL VERIFICATIONS PASSED WITH 100% SUCCESS!')
