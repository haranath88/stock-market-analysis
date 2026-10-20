html = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StockSniper - Today's Stock Summary</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',Arial;background:#f8fafc;color:#1e293b}
header{background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%);color:#fff;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10}
header .logo{display:flex;align-items:center;gap:10px;font-size:24px;font-weight:800;letter-spacing:0.3px}
header .logo span{color:#38bdf8}
header .date{font-size:13px;opacity:0.9;background:rgba(255,255,255,0.12);padding:6px 12px;border-radius:20px}
.container{max-width:1150px;margin:0 auto;padding:20px}
.hero{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.hero-card{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 2px 10px rgba(0,0,0,0.06);border:1px solid #e2e8f0}
.hero-card .label{font-size:11px;color:#64748b;text-transform:uppercase;font-weight:600}
.hero-card b{font-size:26px;color:#0f172a}
.top10{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.07);margin-bottom:24px;border:1px solid #e2e8f0}
.top10 h2{background:#0f172a;color:#fff;padding:14px 18px;font-size:15px;display:flex;justify-content:space-between;align-items:center}
.top10 h2 span{color:#38bdf8;font-weight:400;font-size:13px}
table{width:100%;border-collapse:collapse}
th{font-size:11px;text-transform:uppercase;color:#64748b;background:#f8fafc;padding:11px 12px;text-align:left;letter-spacing:0.5px}
td{padding:11px 12px;font-size:13px;border-top:1px solid #eef2f7}
tr:hover td{background:#f8fafc}
.pos{color:#16a34a;font-weight:700}.neg{color:#dc2626;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;margin:20px 0}
.card{background:#fff;border-radius:14px;padding:18px;text-align:center;box-shadow:0 2px 10px rgba(0,0,0,0.06);border:1px solid #e2e8f0;cursor:pointer;transition:0.2s}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(0,0,0,0.12);border-color:#38bdf8}
.card.active{border:2px solid #0f172a;background:#eff6ff;box-shadow:0 8px 20px rgba(15,23,42,0.15)}
.card .icon{font-size:22px;margin-bottom:6px}
.card h3{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px}
.card .count{font-size:34px;font-weight:800;color:#0f172a}
.card .ytd{font-size:13px;font-weight:700;margin-top:2px}
.detail{background:#fff;border-radius:14px;padding:18px;box-shadow:0 4px 14px rgba(0,0,0,0.06);margin-top:20px;display:none;border:1px solid #e2e8f0}
.detail h3{margin-bottom:10px}
.search{padding:9px 14px;border-radius:22px;border:1px solid #cbd5e1;width:300px;outline:none}
.search:focus{border-color:#0f172a}
footer{text-align:center;color:#94a3b8;font-size:11px;margin:36px 0}
#drop{border:1px dashed #94a3b8;padding:12px;text-align:center;border-radius:12px;margin:0 auto 18px auto;font-size:12px;background:#fff}
.live{font-size:11px;background:#dcfce7;color:#166534;padding:4px 10px;border-radius:12px;font-weight:600}
</style>
</head>
<body>
<header>
<div class="logo">🎯 StockSniper <span>PRO</span></div>
<div class="date" id="headerDate">Loading CSVs...</div>
</header>
<div class="container">
<div class="hero">
<div class="hero-card"><div class="label">Total Stocks Cleaned Today</div><b id="totalStocks">-</b></div>
<div class="hero-card"><div class="label">Best Filter</div><b id="bestFilter">-</b></div>
<div class="hero-card"><div class="label">6 Filters Active</div><b>6</b></div>
<div class="hero-card"><div class="label">Top 10 Buy</div><b style="color:#16a34a">Actionable</b></div>
</div>

<div id="drop">Drop 8 CSVs here or run <code>python -m http.server 8000</code> → localhost:8000 <input type="file" multiple accept=".csv" onchange="handleFiles(this.files)" style="margin-left:10px"></div>

<div class="top10" id="top10Box" style="display:none">
<h2>🎯 TOP 10 STOCKS TO BUY TODAY <span id="todayDate"></span> <span class="live">● Live</span></h2>
<table><thead><tr><th>#</th><th>Symbol</th><th>Reason to Buy</th><th>Days to Hold to Reach Target</th><th>SL</th><th>Target</th><th>YTD</th></tr></thead><tbody id="top10Body"></tbody></table>
<div style="padding:10px;font-size:11px;color:#64748b;background:#fffbeb">StockSniper Logic: Deduplicated (1 stock = 1 row only) | SL = Risk exit | Target = Based on backtest avg weekly return | DYOR - Not financial advice.</div>
</div>

<div class="grid" id="grid"></div>

<div class="detail" id="detail">
<h3 id="detailTitle"></h3>
<div style="display:flex;justify-content:space-between;align-items:center;margin:12px 0;flex-wrap:wrap;gap:10px">
<input id="search" class="search" placeholder="🔍 Search symbol e.g. TBZ" onkeyup="doSearch()">
<span id="count" style="font-size:12px;color:#64748b"></span>
</div>
<div style="overflow:auto;max-height:520px"><table><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
</div>

<footer>StockSniper PRO v1.0 • Data from your local CSVs • Auto-updates daily when you replace CSVs • © 2026</footer>
</div>

<script>
let store={}, current=null;
function handleFiles(files){ for(let f of files){ Papa.parse(f,{header:true,complete:res=>{let n=f.name.replace('.csv','').toUpperCase(); if(n.includes('CONSISTENT_GAINERS')) n='MASTER'; store[n]=res.data.filter(r=>r.SYMBOL); build();}});} document.getElementById('drop').style.display='none'; }

function build(){
 let master=store['MASTER']; let total=master?master.length:Object.values(store).reduce((s,a)=>s+a.length,0);
 let today=new Date().toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'});
 document.getElementById('headerDate').innerText= total + ' stocks | ' + today;
 document.getElementById('totalStocks').innerText= total;
 document.getElementById('todayDate').innerText='- '+today;

 let allCandidates=[];
 let add=(key, reason, hold, sl, target, priority)=>{
  if(!store[key]) return;
  store[key].forEach(r=>{
   let ytd=parseFloat(r.cum_comp_pct||r.avg_weekly_pct||0); if(isNaN(ytd)) ytd=0;
   let avgW=parseFloat(r.avg_weekly_pct||0); if(avgW<=0) avgW=0.5;
   let est=Math.ceil((parseFloat(target)/avgW)*7); if(est<3) est=hold; if(est>60) est=hold;
   allCandidates.push({sym:r.SYMBOL, ytd, reason, hold:`${hold} Days (Est ${est}D to hit +${target}%)`, sl:`-${sl}%`, target:`+${target}%`, priority});
  });
 };
 add("3_CONSISTENT_UP","95% Win | Consistent Up - Never 2 weeks down 52W | Best hold",30,5,15,1);
 add("7_TOP50_GAINERS","Top 50 Gainers YTD | 100% Win | Strong momentum leader",15,6,18,2);
 add("6_STABLE","97% Win | Low drawdown | Stable compounder",25,4,10,3);
 add("5_BURST","Burst Pattern - 2 red then spike | 59% Win",10,8,20,4);
 add("1_PROFIT_BOOKING","Profit booking dip - W1 Up W2 Down | Swing +6.4%",5,4,7,5);
 add("2_MOMENTUM","Momentum - W1 Up W2 Up | Continuation",10,6,12,6);

 allCandidates.sort((a,b)=> b.ytd - a.ytd || a.priority - b.priority);
 let seen=new Set(); let unique=[];
 for(let c of allCandidates){ if(!seen.has(c.sym)){ seen.add(c.sym); unique.push(c); } }
 let top10=unique.slice(0,10);
 if(top10.length>0){
  document.getElementById('top10Box').style.display='block';
  document.getElementById('top10Body').innerHTML=top10.map((c,i)=>`<tr><td>${i+1}</td><td><b>${c.sym}</b></td><td>${c.reason}</td><td><b>${c.hold}</b></td><td class="neg">${c.sl}</td><td class="pos">${c.target}</td><td class="pos">${c.ytd.toFixed(2)}%</td></tr>`).join('');
  document.getElementById('bestFilter').innerText=top10[0].sym;
 } else { document.getElementById('bestFilter').innerText='-'; }

 let order=["1_PROFIT_BOOKING","2_MOMENTUM","3_CONSISTENT_UP","5_BURST","6_STABLE","7_TOP50_GAINERS"];
 let icons={"1_PROFIT_BOOKING":"💰","2_MOMENTUM":"📈","3_CONSISTENT_UP":"🚀","5_BURST":"⚡","6_STABLE":"🛡️","7_TOP50_GAINERS":"🔥"};
 let html=''; order.forEach(k=>{ if(!store[k]) return; let vals=store[k].map(r=>parseFloat(r.cum_comp_pct||0)).filter(v=>!isNaN(v)); let avg=vals.reduce((a,b)=>a+b,0)/(vals.length||1); 
 html+=`<div class="card" id="box-${k}" onclick="show('${k}')"><div class="icon">${icons[k]||'📊'}</div><h3>${k.replace(/^\d+_/,'').replace(/_/g,' ')}</h3><div class="count">${store[k].length}</div><div class="ytd ${avg>=0?'pos':'neg'}">${avg.toFixed(2)}% YTD</div><div style="font-size:11px;color:#64748b;margin-top:4px">Click to view</div></div>`; });
 document.getElementById('grid').innerHTML=html;
}
function show(name){
 current=name;
 document.querySelectorAll('.card').forEach(b=>b.classList.remove('active'));
 let el=document.getElementById('box-'+name); if(el) el.classList.add('active');
 document.getElementById('detail').style.display='block';
 document.getElementById('detailTitle').innerText=name+` • ${store[name].length} stocks - Full list`;
 render(store[name]);
 document.getElementById('detail').scrollIntoView({behavior:'smooth'});
}
function render(data){
 if(!data || data.length==0) return;
 let cols=Object.keys(data[0]||{}).filter(c=>!c.toLowerCase().includes('unnamed')).slice(0,12);
 document.getElementById('thead').innerHTML='<tr>'+cols.map(c=>'<th>'+c+'</th>').join('')+'</tr>';
 document.getElementById('tbody').innerHTML=data.slice(0,500).map(r=>'<tr>'+cols.map(c=>{let v=r[c]||''; let n=parseFloat(v); if(!isNaN(n) && c.toLowerCase().includes('pct')) v=`<span class="${n>=0?'pos':'neg'}">${n.toFixed(2)}%</span>`; return '<td>'+v+'</td>';}).join('')+'</tr>').join('');
 document.getElementById('count').innerText=data.length+' stocks | Showing 500 | Search to filter';
}
function doSearch(){ let q=document.getElementById('search').value.toUpperCase(); let d=q?(store[current]||[]).filter(r=>(r.SYMBOL||'').toUpperCase().includes(q)):store[current]; render(d); }
async function autoLoad(){ let files=["consistent_gainers_weekly.csv","1_PROFIT_BOOKING.csv","2_MOMENTUM.csv","3_CONSISTENT_UP.csv","4_CONSISTENT_DOWN.csv","5_BURST.csv","6_STABLE.csv","7_TOP50_GAINERS.csv"]; let ok=false; for(let fn of files){ try{let r=await fetch(fn); if(!r.ok) continue; let t=await r.text(); let p=Papa.parse(t,{header:true}); let name=fn.replace('.csv','').toUpperCase(); if(name.includes('CONSISTENT_GAINERS')) name='MASTER'; store[name]=p.data.filter(x=>x.SYMBOL); ok=true;}catch(e){} } if(ok){document.getElementById('drop').style.display='none'; build();} }
autoLoad();
</script>
</body>
</html>
"""

with open('index.html','w',encoding='utf-8') as f:
    f.write(html)

print('StockSniper PRO index.html created! Run: python -m http.server 8000 -> http://localhost:8000')