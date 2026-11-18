"""Stream the local catalog, apply gates, then MMR within a source-verified pilot pool."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
csv.field_size_limit(sys.maxsize)
NEEDS = {
 'AI chat pieces': {'tags':['ai.reasoning','ai.tool_activity','ai.sources_citations'], 'items':['@ai-elements/reasoning','@ai-elements/sources','@assistant-ui/elements-tool-call']},
 'Prompt input': {'tags':['input.text','ai.chat'], 'items':['@ai-elements/prompt-input','@assistant-ui/elements-composer','@elements/chat-input']},
 'Code block': {'tags':['content.code'], 'items':['@ai-elements/code-block','@kibo-ui/code-block','@assistant-ui/elements-terminal-block']},
 'Data table': {'tags':['data.table'], 'items':['@kibo-ui/table','@assistant-ui/elements-data-table','@assistant-ui/elements-spec-sheet']},
 'Chart': {'tags':['data.chart'], 'items':['@assistant-ui/elements-chart','@kibo-ui/contribution-graph','@kibo-ui/gantt']},
 'Files and attachments': {'tags':['files.browse','files.upload','files.document'], 'items':['@ai-elements/file-tree','@assistant-ui/elements-file-tree','@kibo-ui/dropzone']},
 'Command palette and search': {'tags':['data.search'], 'items':['@assistant-ui/elements-command-palette','@assistant-ui/elements-conversation-search','@kibo-ui/combobox']},
 'Toast and inline feedback': {'tags':['feedback.notification','feedback.state'], 'items':['@coss/toast','@kibo-ui/banner','@assistant-ui/elements-error-state']},
}
REPOS = {'@ai-elements':'vercel/ai-elements','@assistant-ui':'assistant-ui/assistant-ui','@kibo-ui':'shadcnblocks/kibo','@elements':'crafter-station/elements','@diceui':'sadmann7/diceui','@coss':'cosscom/ui'}
SIGNALS = {
 'AI chat pieces': [('detail_changed','expansion/collapse of reasoning and tool details','Wrap user-triggered disclosure changes with section type, initial state and opportunity_summary; F02.'),('object_opened','opening a cited source','Bind owned reference IDs and emit object_opened/object_left; F05. No URLs in telemetry.')],
 'Prompt input': [('keyboard_summary','coarse typing rhythm, pauses and correction-share buckets','Summarize transient samples on-device; exclude sensitive controls; no raw keys or exact timing in observations.'),('composer_summary','draft shape, paste share and editing transactions','Wire coarse character/line buckets and editor transaction counts; no draft text in observations; F11–F13.'),('draft_state','explicitly saving, restoring or discarding a draft','Wire draft lifecycle and consent; deleted wording belongs only to the separate local 30-day content store, never analytics.'),('message_revised','editing a submitted prompt','Emit after explicit revision; corrections alone do not establish response quality.')],
 'Code block': [('output_action','copying or exporting displayed code','Wire explicit copy/download success with output kind and opportunity_summary; F04; never clipboard contents.')],
 'Data table': [('collection_control_changed','sorting and filtering rows','Instrument user changes with allowlisted control IDs and opportunity_summary; F09.'),('representation_changed','switching table and chart for the same dataset','Add a second representation and user-triggered switch instrumentation; F06.')],
 'Chart': [('representation_changed','switching a chart to a table','Provide the same underlying dataset in both representations; emit opportunity_summary and user switches; F06.'),('collection_control_changed','changing a chart range or filter','Add allowlisted filters and distinguish defaults from user actions; F09.')],
 'Files and attachments': [('attachment_state','adding/removing files and submission attachment counts','Wire upload lifecycle to owned file references and message_submitted; no filenames, paths or contents in analytics; F14.'),('object_opened','opening or revisiting an attachment','Bind stable owned content identity and emit object_opened/object_left; F05.')],
 'Command palette and search': [('search_started','search episodes and refinement','Wire search_results/search_refined/search_result_opened/search_closed with result rank and no query text; F08.'),('action_invoked','keyboard and command activation','Capture semantic action ID and modality, with eligible opportunities; F01/F10; never raw key sequences.')],
 'Toast and inline feedback': [('action_invoked','explicit undo, retry or dismissal','Bind visible actions to allowlisted semantic IDs and opportunity_summary; F01.'),('error_state','observable recovery after an error','Connect retry to the actual operation outcome; F18. Dismissal does not establish satisfaction.')],
}

def fetch(url):
    assert url.startswith('https://')
    return subprocess.check_output(['curl','--fail','--silent','--show-error','--location','--max-time','45',url])


def licence(ns):
    repo = REPOS[ns]
    evidence_dir = ROOT/'data/evidence'; evidence_dir.mkdir(exist_ok=True)
    cache = evidence_dir/(ns[1:]+'-license.json')
    if cache.exists(): return json.loads(cache.read_text())
    sha = json.loads(fetch(f'https://api.github.com/repos/{repo}/commits/HEAD'))['sha']
    for name in ['LICENSE','LICENSE.md','license.md']:
        try: body = fetch(f'https://raw.githubusercontent.com/{repo}/{sha}/{name}').decode(); break
        except Exception: body = ''
    verified = bool(body) and ('Permission is hereby granted' in body or 'Apache License, Version 2.0' in body)
    if any(t in body for t in ['Commons Clause','Non-Commercial','Noncommercial']): verified=False
    result = {'name': 'MIT' if 'Permission is hereby granted' in body else 'Apache-2.0' if 'Apache License, Version 2.0' in body else 'Unverified', 'verified':verified,'url':f'https://github.com/{repo}/blob/{sha}/{name}','repository':repo,'revision':sha,'sha256':hashlib.sha256(body.encode()).hexdigest()}
    cache.write_text(json.dumps(result,indent=2)); (evidence_dir/(ns[1:]+'-LICENSE.txt')).write_text(body)
    return result


def similar(a,b):
    j = lambda x,y: len(set(x)&set(y))/max(1,len(set(x)|set(y)))
    return .25*j(a['tags'],b['tags']) + .25*j(a['dependencies'],b['dependencies']) + .2*(a['registry']==b['registry']) + .15*(a['pattern']==b['pattern']) + .15*(a.get('layout')==b.get('layout'))


def mmr(items, count=3):
    selected=[]; counts=collections.Counter()
    while items and len(selected)<count:
        eligible=[x for x in items if counts[x['registry']]<2]
        if not eligible:break
        winner=max(eligible,key=lambda x:(.75*x['score']-.25*max([similar(x,s) for s in selected] or [0]),x['id']))
        selected.append(winner);counts[winner['registry']]+=1;items.remove(winner)
    return selected


def main():
    global NEEDS, REPOS, SIGNALS
    parser=argparse.ArgumentParser()
    parser.add_argument('--wave',default='pilot-01')
    parser.add_argument('--config',type=Path)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,40}',args.wave):parser.error('Wave names use 1–40 lowercase letters, digits or hyphens')
    if args.config:
        config=json.loads(args.config.read_text())
        NEEDS,REPOS,SIGNALS=config['needs'],config['repositories'],config['signals']
    wanted={x for n in NEEDS.values() for x in n['items']}; rows={}; seen=set(); stats=collections.Counter()
    for r in csv.DictReader(open(ROOT.parent/'Implicity_component_catalog.csv')):
        stats['records']+=1
        if r['ui_artifact_candidate']!='true':continue
        tags=json.loads(r['functional_tags_json'])
        if 'product.marketing' in tags or r['artifact_role'] in ('example','marketing_block') or r['item_type']=='registry:example' or 'example' in r['component_name'] or 'demo' in r['component_name']:continue
        if r['origin_resolution_status']!='publisher_entry':continue
        claim=json.loads(r['publisher_license_claim_json'] or 'null') or {}
        if claim.get('is_pro') or str(claim.get('access','')).lower() in ('paid','pro') or str(claim.get('tier','')).lower() in ('paid','pro'):continue
        keys=(r['component_address'],r['item_metadata_sha256'])
        if any(x and x in seen for x in keys):continue
        seen.update(x for x in keys if x);stats['gate_passed']+=1
        if r['component_address'] in wanted:rows[r['component_address']]=r
    missing=wanted-rows.keys();assert not missing,missing
    assert all(re.fullmatch(r'@[a-zA-Z0-9_-]+',ns) for ns in REPOS)
    licenses={ns:licence(ns) for ns in REPOS}
    previous={c['id']:c for c in json.loads((ROOT/'data/candidates.json').read_text())} if (ROOT/'data/candidates.json').exists() else {}
    out=[]
    for need,spec in NEEDS.items():
        pool=[]
        for address in spec['items']:
            r=rows[address];tags=json.loads(r['functional_tags_json'])
            assert any(tag==t or tag.startswith(t+'.') for tag in tags for t in spec['tags']),address
            evidence=licenses[r['registry_namespace']];assert evidence['verified'],evidence
            slug=re.sub(r'[^a-z0-9-]','-',address.lower()).strip('-')
            cache=ROOT/'data/evidence'/f'{slug}.json'
            if cache.exists(): payload=cache.read_bytes()
            else:payload=fetch(r['item_json_url_candidate']);cache.write_bytes(payload)
            item=json.loads(payload)
            sources='\n'.join(f.get('content','') for f in item.get('files',[]))
            assert re.search(r'\b(React|react|jsx|tsx)\b',sources) or any(f.get('path','').endswith(('.tsx','.jsx')) for f in item.get('files',[])),address
            deps=item.get('dependencies',[]) or []
            a11y=sum(bool(re.search(p,sources)) for p in ['aria-','onKeyDown|onKeyUp','focus|Focus','<button|Button|Trigger'])
            states=sum(bool(re.search(p,sources,re.I)) for p in ['loading|pending|streaming','empty|no results|no items','error|failed'])
            rubric={'fit':5,'accessibility_evidence':a11y,'state_evidence':states,'dependency_cost':max(0,5-len(deps)//2),'portability':max(0,5-len(sources)//18000),'licence':5}
            pattern=next((p for p in ['reasoning','sources','tool','composer','input','terminal','code','spec-sheet','table','chart','gantt','graph','tree','dropzone','conversation-search','command','combobox','toast','banner','error'] if p in address),'other')
            version=hashlib.sha256(payload).hexdigest()
            pool.append({'id':slug,'address':address,'addressUrl':r['item_json_url_candidate'],'registry':r['registry_namespace'],'name':r['title'] or r['component_name'],'need':need,'wave':args.wave,'version':version,'sourceRevision':'registry-sha256:'+version,'repositoryRevision':evidence['revision'],'metadataHash':r['item_metadata_sha256'],'license':evidence,'tags':tags,'dependencies':deps,'registryDependencies':item.get('registryDependencies',[]),'portingEffort':('High' if len(sources)>25000 else 'Medium' if len(sources)>6000 else 'Low')+' — rewrite Tailwind classes, preserve behaviour, test token themes and density','rubric':rubric,'score':sum(rubric.values())/27,'pattern':pattern,'layout':('tabular' if re.search(r'<table|TableProvider|<thead',sources) else 'chart' if re.search(r'<svg|recharts',sources) else 'grid' if 'grid-cols-' in sources else 'stacked' if 'flex-col' in sources else 'inline'),'why':f'Matches item-level {", ".join(tags)}; {pattern} interaction provides a distinct pilot comparison. Static source shows {a11y}/4 accessibility indicators and {states}/3 state indicators; these are evidence hints, not a passed accessibility audit. Permissive repository licence verified at a pinned commit.','signals':[{'event':e,'possible':'Makes possible: '+p+'.','integration':i} for e,p,i in SIGNALS[need] if not (need=='AI chat pieces' and ((pattern=='sources' and e=='detail_changed') or (pattern!='sources' and e=='object_opened'))) and not (need=='Files and attachments' and ((pattern=='dropzone' and e=='object_opened') or (pattern!='dropzone' and e=='attachment_state')))],'previews':{}})
        out.extend(mmr(pool))
    # Check all referenced events against the actual observation contract, without storing the full schema.
    contract=json.loads((ROOT.parent/'packages/contracts/observations.schema.json').read_text())
    events={item['properties']['event_name']['const'] for item in contract['anyOf']}
    for c in out:
        for signal in c['signals']:assert signal['event'] in events,signal['event']
    for c in out:
        old=previous.get(c['id'])
        if old and old['version']==c['version']:
            c['previews']=old.get('previews',{})
            if 'addedSize' in old:c['addedSize']=old['addedSize']
    current_ids={c['id'] for c in out}
    out=[c for c in previous.values() if c.get('wave')!=args.wave and c['id'] not in current_ids]+out
    fixtures=json.loads((ROOT/'scripts/preview/fixtures.json').read_text())
    for c in out:
        packages=fixtures.get(c['id'],{}).get('packages',[])
        if packages:c['why']+=' Preview compatibility pins: '+', '.join(packages)+'. Recheck dependency compatibility before porting.'
    digest=hashlib.sha256()
    with open(ROOT.parent/'Implicity_component_catalog.csv','rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    (ROOT/'data/candidates.json').write_text(json.dumps(out,indent=2))
    (ROOT/'data'/('shortlist-run.json' if args.wave=='pilot-01' else args.wave+'-run.json')).write_text(json.dumps({'wave':args.wave,'stats':stats,'needs':NEEDS,'method':'Source-reviewed pilot pool (explicit addresses); 0.75 relevance - 0.25 max similarity; similarity = tags .25, dependencies .25, registry .20, interaction pattern .15, layout .15; max 2 per registry per need. No popularity scores. Scores are static-source evidence, not verified runtime quality.','catalog_sha256':digest.hexdigest()},indent=2))
    print(f'Built {len(out)} candidates across {len(NEEDS)} needs')

if __name__=='__main__':main()
