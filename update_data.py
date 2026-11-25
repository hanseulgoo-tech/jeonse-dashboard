import json, os, pathlib, urllib.request, urllib.parse, datetime, re, math
from zoneinfo import ZoneInfo
P=pathlib.Path(__file__).parent
key=os.environ['REB_API_KEY']
base='https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do'
store=json.loads((P/'data.json').read_text()); codes={x['code']:x['id'] for x in json.loads((P/'region_codes.json').read_text())}; rows={r['id']:r for r in store['data']}
def month(n): return f'{n//12:04d}{n%12+1:02d}'
def index(s):
 m=re.fullmatch(r'(\d{4})년 (\d{1,2})월',s);return int(m[1])*12+int(m[2])-1
first=index(store['months'][0]);last=index(store['months'][-1]);now=datetime.datetime.now(ZoneInfo('Asia/Seoul')); end=now.year*12+now.month-1;start=max(first,last-2)
updates={}
for n in range(start,end+1):
 stamp=month(n); page=1; received=0
 while True:
  q=dict(KEY=key,Type='json',pIndex=page,pSize=1000,STATBL_ID='A_2024_00072',DTACYCLE_CD='MM',START_WRTTIME=stamp,END_WRTTIME=stamp)
  try:
   with urllib.request.urlopen(base+'?'+urllib.parse.urlencode(q),timeout=60) as f: payload=json.load(f)
  except Exception as e: raise RuntimeError('API transport failure: '+type(e).__name__) from None
  if 'RESULT' in payload:
   if payload['RESULT'].get('CODE')=='INFO-200':break
   raise RuntimeError('API status: '+str(payload['RESULT'].get('CODE')))
  blocks=payload.get('SttsApiTblData');
  if not isinstance(blocks,list):raise RuntimeError('Unexpected API schema')
  records=next((b['row'] for b in blocks if 'row' in b),[])
  total=next((h['list_total_count'] for b in blocks for h in b.get('head',[]) if 'list_total_count' in h),None)
  if not records:raise RuntimeError('Empty response page')
  for r in records:
   if str(r.get('ITM_ID'))!='100001':continue
   code=str(r.get('CLS_ID')); date=re.sub(r'[^0-9]','',str(r.get('WRTTIME_IDTFR_ID','')))
   if date!=stamp:raise RuntimeError('Unexpected date field or period filter')
   if code not in codes:raise RuntimeError('Unknown region code: '+code)
   raw=r.get('DTA_VAL');v=None if raw is None or str(raw).strip() in ('','-','—') else float(raw)
   if v is not None and (not math.isfinite(v) or not 0<=v<=200):raise RuntimeError('Invalid value')
   k=(n,codes[code]);
   if k in updates and updates[k]!=v:raise RuntimeError('Conflicting duplicate')
   updates[k]=v
  received+=len(records)
  if total is not None and received>=int(total) or total is None and len(records)<1000:break
  page+=1
  if page>100:raise RuntimeError('Pagination limit')
 if n<=last or any(k[0]==n for k in updates):
  valid=sum(v is not None for (m,i),v in updates.items() if m==n)
  if valid<200 or updates.get((n,3)) is None:raise RuntimeError(f'Incomplete month {stamp}: {valid} valid rows')
if not updates:raise RuntimeError('No usable data')
newlast=max(last,max(n for (n,i),v in updates.items() if v is not None))
for n in range(last+1,newlast+1):
 if updates.get((n,3)) is None:raise RuntimeError('Gap in new months')
 store['months'].append(f'{n//12}년 {n%12+1}월')
 for r in rows.values():r['v'].append(None)
for (n,i),v in updates.items():
 if n<=newlast:rows[i]['v'][n-first]=v
store['updated']=now.strftime('%Y-%m-%d %H:%M KST');tmp=P/'data.tmp';tmp.write_text(json.dumps(store,ensure_ascii=False,allow_nan=False));tmp.replace(P/'data.json');print('Validated months:',len(store['months']))
