const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname,'../counter/static/counter/app.js'),'utf8');
const detection = {count:2,boxes:[{x:40,y:30,width:100,height:220,score:.9}],image:'data:image/jpeg;base64,test',processing_ms:180,over_capacity:false};

function harness(overrides={}) {
  const elements=new Map(),timers=new Map(),calls=[];
  let nextTimer=1;
  function element(id) {
    if(!elements.has(id))elements.set(id,{
      hidden:['video','result','overlay','frameLabel'].includes(id),
      value:id==='capacity'?'24':id==='threshold'?'0.35':'sample',
      attrs:new Map(id==='overlay'?[['hidden','']]:[]), children:[],
      classList:{toggle(){}},style:{},files:[],videoWidth:640,videoHeight:480,ended:false,
      addEventListener(){},setAttribute(k,v){this.attrs.set(k,String(v));if(k==='id')elements.set(String(v),this);},
      getAttribute(k){return this.attrs.get(k)??null;},removeAttribute(k){this.attrs.delete(k);},
      replaceChildren(...children){this.children=children;},append(...children){this.children.push(...children);},appendChild(child){this.children.push(child);return child;},
      pause(){this.paused=true;},load(){},async play(){this.paused=false;},
      getContext(){return {drawImage(){}};},toBlob(callback){callback({jpeg:true});},
    });
    return elements.get(id);
  }
  element('video').parentElement=element('viewport');
  const response=data=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>data});
  const sandbox={
    document:{getElementById:id=>id==='overlay'&&overrides.missingOverlay&&!elements.has(id)?null:element(id),cookie:'csrftoken=test',createElement:()=>element('new'),createElementNS:(ns,tag)=>element('svg-'+tag+'-'+elements.size),createTextNode:text=>({textContent:text})},
    window:{addEventListener(){}},navigator:{},
    Image:class {constructor(){this.naturalWidth=640;this.naturalHeight=480;}set src(v){queueMicrotask(()=>this.onload());}},
    URL:{revokeObjectURL(){}},FormData:class{append(){}},
    fetch:async(url,options)=>{
      calls.push(url);
      if(url==='/api/sessions/'&&options?.method==='POST')return overrides.create?overrides.create(response):response({id:'test-id'});
      if(url==='/api/sessions/')return response({sessions:[]});
      if(url.endsWith('/stop/'))return response({ok:true});
      if(url.endsWith('/frames/'))return overrides.frame?overrides.frame(response):response(detection);
      throw new Error('Petición inesperada '+url);
    },
    setTimeout(callback,ms){const id=nextTimer++;timers.set(id,{callback,ms});return id;},
    clearTimeout(id){timers.delete(id);},queueMicrotask,console,
  };
  vm.createContext(sandbox);vm.runInContext(source,sandbox);
  return {element,timers,calls,run:code=>vm.runInContext(code,sandbox)};
}

test('detener durante la creación cierra la sesión que llega tarde',async()=>{
  let completeCreation,started;
  const ready=new Promise(resolve=>started=resolve);
  const h=harness({create:response=>{started();return new Promise(resolve=>completeCreation=()=>resolve(response({id:'late-id'})));}});
  const starting=h.run("start('sample')");await ready;await h.run('finish(false)');completeCreation();await starting;
  assert.ok(h.calls.includes('/api/sessions/late-id/stop/'));
  assert.equal(h.calls.some(url=>url.endsWith('/frames/')),false);
  assert.equal(h.run('sessionId'),null);assert.equal(h.run('running'),false);
});

test('el video sigue visible mientras se espera y se recibe la detección',async()=>{
  let completeFrame,started;
  const ready=new Promise(resolve=>started=resolve);
  const h=harness({frame:response=>{started();return new Promise(resolve=>completeFrame=()=>resolve(response(detection)));}});
  h.run("sessionId='test-id';running=true;showLivePreview()");
  const pending=h.run('processFrame(video)');await ready;
  assert.equal(h.element('video').hidden,false);assert.equal(h.element('result').hidden,true);
  assert.equal(h.element('overlay').getAttribute('hidden'),null);
  completeFrame();await pending;
  assert.equal(h.element('video').hidden,false);assert.equal(h.element('result').hidden,true);
  assert.equal(h.element('overlay').getAttribute('viewBox'),'0 0 640 480');
  assert.equal(h.element('overlay').children.length,2);
  h.run('release()');
});

test('una detección vacía elimina recuadros anteriores sin ocultar el video',()=>{
  const h=harness();h.run('showLivePreview()');
  h.run('drawDetections([{x:10,y:20,width:50,height:100,score:.8}],800,450)');
  assert.equal(h.element('overlay').children.length,2);
  assert.equal(h.element('overlay').getAttribute('viewBox'),'0 0 800 450');
  h.run('drawDetections([],800,450)');
  assert.equal(h.element('overlay').children.length,0);assert.equal(h.element('video').hidden,false);
  h.run('release()');
});

test('los recuadros caducan después de 1200 ms sin detener el video',()=>{
  const h=harness();h.run('showLivePreview();drawDetections([{x:0,y:0,width:20,height:30,score:.9}],640,480)');
  const stale=[...h.timers.values()].find(timer=>timer.ms===1200);
  assert.ok(stale);stale.callback();
  assert.equal(h.element('overlay').children.length,0);assert.equal(h.element('video').hidden,false);
  h.run('release()');
});

test('detener conserva la última detección como imagen y libera el video',async()=>{
  const h=harness();h.run("sessionId='test-id';running=true;showLivePreview()");
  await h.run('processFrame(video)');await h.run('finish(false)');
  assert.equal(h.element('video').hidden,true);assert.equal(h.element('video').paused,true);
  assert.equal(h.element('result').hidden,false);assert.equal(h.element('result').src,detection.image);
  assert.equal(h.element('overlay').getAttribute('hidden'),'');assert.equal(h.timers.size,0);
});

test('no se envían dos inferencias simultáneas y se elimina el temporizador al detener',async()=>{
  let completeFrame,started;
  const ready=new Promise(resolve=>started=resolve);
  const h=harness({frame:response=>{started();return new Promise(resolve=>completeFrame=()=>resolve(response(detection)));}});
  h.run("sessionId='test-id';running=true;showLivePreview()");
  const first=h.run('loop()');await ready;await h.run('loop()');
  assert.equal(h.calls.filter(url=>url.endsWith('/frames/')).length,1);
  completeFrame();await first;
  const loopId=h.run('loopTimer');assert.ok(h.timers.has(loopId));
  assert.ok(h.timers.get(loopId).ms<=250);
  await h.run('finish(false)');assert.equal(h.timers.size,0);assert.equal(h.run('loopTimer'),null);
});

test('las imágenes estáticas siguen mostrando el JPEG anotado',async()=>{
  const h=harness();h.run("sessionId='test-id';running=true");
  await h.run('processFrame({naturalWidth:640,naturalHeight:480})');
  assert.equal(h.element('result').hidden,false);assert.equal(h.element('result').src,detection.image);
  assert.equal(h.element('video').hidden,true);
  assert.equal(h.element('frameLabel').textContent,'OPENCV · YOLOX DNN');
});

test('una plantilla anterior sin SVG crea la capa una sola vez y permite detectar',async()=>{
  const h=harness({missingOverlay:true});
  assert.equal(h.run("$('overlay')"),null);
  h.run("sessionId='test-id';running=true;showLivePreview()");
  assert.equal(h.element('viewport').children.length,1);
  assert.equal(h.element('overlay').getAttribute('preserveAspectRatio'),'xMidYMid meet');
  assert.equal(h.element('overlay').getAttribute('hidden'),null);
  assert.equal(h.element('video').style.opacity,'1');
  await h.run('processFrame(video)');
  assert.equal(h.element('viewport').children.length,1);
  assert.equal(h.element('overlay').children.length,2);
  await h.run('finish(false)');
  assert.equal(h.element('start').disabled,false);assert.equal(h.run('sessionId'),null);
});

test('cerrar una plantilla sin SVG libera la cámara y restaura los controles',async()=>{
  const h=harness({missingOverlay:true});
  h.run("sessionId='test-id';running=true;globalThis.trackStopped=false;stream={getTracks:()=>[{stop:()=>{globalThis.trackStopped=true}}]}");
  await h.run('finish(false)');
  assert.equal(h.run('trackStopped'),true);
  assert.equal(h.run("$('overlay')"),null);
  assert.equal(h.element('video').paused,true);
  assert.equal(h.element('start').disabled,false);
  assert.equal(h.run('finishing'),null);
  assert.ok(h.calls.includes('/api/sessions/test-id/stop/'));
});
