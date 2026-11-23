const {chromium, webkit} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const engine = process.env.BUTLER_BROWSER === 'webkit' ? webkit : chromium;
  const browser = await engine.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1500,height:1050}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.setContent('<body style="margin:0"></body>');
    await page.addScriptTag({path:path.join(__dirname,'../custom_components/biofects_butler/frontend/biofects-butler-panel.js')});
    await page.evaluate(() => {
      const panel=document.createElement('biofects-butler-panel');
      panel._load=async()=>{};
      panel._hass={states:{},panels:{},callService(){throw Error('Editing must not operate devices');},async callWS(message){
        if(message.type==='biofects_butler/save_dashboard_profile'){window.saved=JSON.parse(JSON.stringify(message.profile));return {profile:window.saved};}
        return {profiles:[]};
      }};
      panel._draft={schema_version:1,profile_id:'demo',name:'Our home',default_screen_id:'home',screens:[{screen_id:'home',title:'Home',composition:'freeform_grid',grid_columns:6,sections:[
        {section_id:'controls',slot:'controls',title:'Lights',type:'entity_controls',column_span:2,row_span:1,grid_column:1,grid_row:1,bindings:[{kind:'entity',target_id:'light.one'},{kind:'entity',target_id:'light.two'}],actions:[{gesture:'hold',type:'call_service',domain:'script',service:'good_night',source_id:'light.one'}]},
        {section_id:'assistant',slot:'assistant',title:'Butler',type:'assistant',column_span:2,row_span:1,grid_column:3,grid_row:1,bindings:[],actions:[]}
      ]}]};
      panel._snapshot={profiles:[panel._draft],displays:[]};panel._selectedId='demo';panel._activeWorkspace='screens';panel._activeScreenId='home';panel._activeSectionSlot='controls';
      document.body.append(panel);
    });
    const draft=()=>page.evaluate(()=>document.querySelector('biofects-butler-panel')._draft);
    assert.equal(await page.locator('.page-layout-options').getAttribute('open'),null);
    await page.locator('[data-quick-panel]').selectOption('1');
    await page.locator('[data-quick-position]').selectOption('top_right');
    assert.equal((await draft()).screens[0].sections[1].grid_column,5);
    await page.getByRole('button',{name:'Move panel down',exact:true}).click();
    assert.equal((await draft()).screens[0].sections[1].grid_row,2);
    await page.locator('.simple-panel-controls [data-action="undo-grid"]').click();
    assert.equal((await draft()).screens[0].sections[1].grid_row,1);
    await page.locator('[data-quick-size="column_span"]').selectOption('3');
    assert.equal((await draft()).screens[0].sections[1].grid_column,4);
    await page.locator('[data-quick-size="row_span"]').selectOption('2');
    assert.equal((await draft()).screens[0].sections[1].row_span,2);
    await page.locator('[data-quick-panel]').selectOption('0');
    await page.locator('[data-binding-card]').first().click();
    await page.getByRole('button',{name:'Move card down',exact:true}).click();
    assert.deepEqual((await draft()).screens[0].sections[0].bindings.map(b=>b.target_id),['light.two','light.one']);
    assert.equal((await draft()).screens[0].sections[0].actions[0].service,'good_night');
    await page.getByRole('button',{name:'Save changes',exact:true}).click();
    assert.equal(await page.evaluate(()=>window.saved.screens[0].sections[1].grid_row),1);
    await page.setViewportSize({width:390,height:844});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Phone editor must fit viewport');
    await page.screenshot({path:path.join('/tmp',`butler-simple-editor-${process.env.BUTLER_BROWSER || 'chromium'}.png`),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('Passed: panel selection, positioning, nudge, sizes, undo, card order, save and mobile layout ('+(process.env.BUTLER_BROWSER||'chromium')+')');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
