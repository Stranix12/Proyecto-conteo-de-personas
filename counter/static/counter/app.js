'use strict';
const $ = id => document.getElementById(id);
const csrf = () => document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1];
let sessionId = null, stream = null, fileURL = null, running = false, busy = false, pending = Promise.resolve(), sampleImage = null, finishing = null;
let livePreview = false, lastResultImage = null, loopTimer = null, overlayTimer = null;
const DETECTION_INTERVAL_MS = 250, OVERLAY_MAX_AGE_MS = 1200;
const canvas = $('canvas'), video = $('video');
function detectionOverlay(){
  let overlay=$('overlay');
  // Una plantilla ya cargada puede ser anterior a la capa SVG de esta versión.
  if(!overlay){
    overlay=document.createElementNS('http://www.w3.org/2000/svg','svg');
    overlay.setAttribute('id','overlay');
    overlay.setAttribute('preserveAspectRatio','xMidYMid meet');
    overlay.setAttribute('aria-hidden','true');
    overlay.setAttribute('hidden','');
    video.parentElement.appendChild(overlay);
  }
  // Estos estilos también permiten recuperar una página con el CSS anterior.
  Object.assign(overlay.style,{position:'absolute',inset:'0',width:'100%',height:'100%',pointerEvents:'none',zIndex:'2'});
  video.style.opacity='1';video.style.zIndex='1';$('frameLabel').style.zIndex='3';
  return overlay;
}
function showLivePreview(){
  const overlay=detectionOverlay();
  livePreview=true;lastResultImage=null;
  $('empty').hidden=true;$('result').hidden=true;video.hidden=false;
  overlay.replaceChildren();overlay.removeAttribute('hidden');$('frameLabel').hidden=false;
  $('frameLabel').textContent='VIDEO CONTINUO · DETECCIÓN PERIÓDICA';
}
function drawDetections(boxes,width,height){
  const overlay=detectionOverlay(),ns='http://www.w3.org/2000/svg';
  clearTimeout(overlayTimer);
  overlay.setAttribute('viewBox',`0 0 ${width} ${height}`);
  overlay.replaceChildren();
  for(const box of boxes){
    const rect=document.createElementNS(ns,'rect');
    for(const [key,value] of Object.entries({x:box.x,y:box.y,width:box.width,height:box.height}))rect.setAttribute(key,value);
    rect.setAttribute('fill','none');rect.setAttribute('stroke','#64eb3c');rect.setAttribute('stroke-width','2');rect.setAttribute('vector-effect','non-scaling-stroke');
    const label=document.createElementNS(ns,'text');
    label.setAttribute('x',box.x+3);label.setAttribute('y',Math.max(16,box.y-5));
    label.setAttribute('fill','#a8ff83');label.setAttribute('font-size','15');
    label.setAttribute('stroke','#20271f');label.setAttribute('stroke-width','3');label.setAttribute('paint-order','stroke');
    label.textContent=`Persona ${Number(box.score).toFixed(2)}`;
    overlay.append(rect,label);
  }
  // No se presentan recuadros antiguos como detecciones actuales si el servidor tarda.
  overlayTimer=setTimeout(()=>overlay.replaceChildren(),OVERLAY_MAX_AGE_MS);
}
function message(text, error=false) { $('status').textContent=text; $('alert').hidden=!error; $('alert').textContent=error ? text : ''; }
async function api(url, data, json=false) {
  const response = await fetch(url, {method:'POST',headers:{'X-CSRFToken':csrf(),...(json?{'Content-Type':'application/json'}:{})},body:json?JSON.stringify(data):data});
  const type = response.headers.get('content-type') || '';
  const result = type.includes('application/json') ? await response.json() : {};
  if (!response.ok) throw new Error(result.error || `Error del servidor (${response.status}). Revisa PostgreSQL y vuelve a intentar.`);
  return result;
}
function controls(active){ ['start','source','capacity','file','example'].forEach(id=>$(id).disabled=active); $('stop').disabled=!active; $('liveDot').classList.toggle('muted',!active); }
async function history(){
  try{
    const response = await fetch('/api/sessions/');
    if(!response.ok) throw new Error('No se pudo consultar PostgreSQL.');
    const data = await response.json();
    $('historyBody').replaceChildren();
    if(!data.sessions.length) {$('historyBody').innerHTML='<tr><td colspan="6">Aún no hay sesiones. Inicia un conteo o prueba el ejemplo.</td></tr>';return;}
    for(const s of data.sessions){
      const tr=document.createElement('tr');
      [new Date(s.started).toLocaleString('es-EC'),s.source,s.ended?'Finalizada':'Activa',s.samples,s.peak,s.mean].forEach((value,i)=>{const td=document.createElement('td');if(i===2){const span=document.createElement('span');span.className='pill';span.textContent=value;td.append(span);}else td.textContent=value;tr.append(td);});
      $('historyBody').append(tr);
    }
  }catch(e){message(e.message,true);}
}
async function processFrame(source){
  const w = source.videoWidth || source.naturalWidth, h=source.videoHeight || source.naturalHeight;
  if(!w || !h) throw new Error('La fuente todavía no tiene una imagen disponible.');
  const ratio=Math.min(1,800/w,600/h);
  canvas.width=Math.max(64,Math.round(w*ratio));canvas.height=Math.max(64,Math.round(h*ratio));
  canvas.getContext('2d').drawImage(source,0,0,canvas.width,canvas.height);
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.85));
  if(!blob)throw new Error('No se pudo capturar la imagen.');
  const form=new FormData();form.append('frame',blob,'frame.jpg');form.append('threshold',$('threshold').value);
  const data=await api(`/api/sessions/${sessionId}/frames/`,form);
  if(source===video&&livePreview){
    lastResultImage=data.image;
    if(running)drawDetections(data.boxes,canvas.width,canvas.height);
  }else{
    $('empty').hidden=true;$('result').hidden=false;$('result').src=data.image;
    $('frameLabel').hidden=false;$('frameLabel').textContent='OPENCV · YOLOX DNN';
  }
  $('count').textContent=data.count;const capacity=Number($('capacity').value);const percentage=Math.round(data.count/capacity*100);
  $('occupancy').replaceChildren(document.createTextNode(percentage),Object.assign(document.createElement('span'),{textContent:'%'}));
  $('meter').style.width=Math.min(100,percentage)+'%';$('latency').textContent=Math.round(data.processing_ms);
  $('capacityLabel').textContent=`aforo de ${capacity} persona${capacity===1?'':'s'}`;
  message(data.over_capacity?'El conteo supera el aforo configurado.':`${data.count} persona${data.count===1?'':'s'} detectada${data.count===1?'':'s'} · lectura guardada`,data.over_capacity);
}
async function loop(){
  if(!running||busy)return;
  if(video.ended){await finish();return;}
  const started=Date.now();
  busy=true;
  pending=processFrame(video);
  try{await pending;}catch(e){running=false;message(e.message,true);}finally{busy=false;}
  if(running)loopTimer=setTimeout(loop,Math.max(0,DETECTION_INTERVAL_MS-(Date.now()-started)));else await finish(false);
}
function release(){
  clearTimeout(loopTimer);loopTimer=null;clearTimeout(overlayTimer);overlayTimer=null;
  // Liberar primero los dispositivos, aunque la página no tenga la capa SVG.
  stream?.getTracks().forEach(t=>t.stop());stream=null;
  video.pause();video.srcObject=null;video.removeAttribute('src');video.load();
  if(fileURL)URL.revokeObjectURL(fileURL);fileURL=null;sampleImage=null;
  const overlay=$('overlay');overlay?.replaceChildren();overlay?.setAttribute('hidden','');video.hidden=true;
  if(livePreview){
    if(lastResultImage){$('result').src=lastResultImage;$('result').hidden=false;$('frameLabel').textContent='ÚLTIMA DETECCIÓN · SESIÓN DETENIDA';}
    else{$('result').hidden=true;$('empty').hidden=false;$('frameLabel').hidden=true;}
  }
  livePreview=false;lastResultImage=null;
}
async function finish(showMessage=true){
  if(finishing)return finishing;
  finishing=finishOnce(showMessage);
  try{return await finishing;}finally{finishing=null;}
}
async function finishOnce(showMessage){
  running=false;clearTimeout(loopTimer);loopTimer=null;$('stop').disabled=true;
  try{await pending;}catch(e){}
  release();
  let failed=false;
  if(sessionId){try{await api(`/api/sessions/${sessionId}/stop/`,{} ,true);sessionId=null;}catch(e){message(e.message,true);failed=true;}}
  controls(false);if(failed)$('stop').disabled=false;if(showMessage&&!failed)message('Sesión finalizada. Las lecturas están guardadas.');await history();
}
async function loadImage(url){const img=new Image();await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error('No se pudo abrir la imagen.'));img.src=url;});return img;}
async function start(mode){
  if(running||busy||finishing)return;
  if(sessionId){message('La sesión anterior no pudo cerrarse. Pulsa Detener sesión para reintentar.',true);$('stop').disabled=false;return;}
  const capacity=Number($('capacity').value);
  if(!Number.isInteger(capacity)||capacity<1||capacity>1000){message('El aforo debe ser un entero de 1 a 1000.',true);return;}
  controls(true);running=true;message('Preparando fuente…');
  try{
    if(mode==='sample')sampleImage=await loadImage('/static/counter/sample.png');
    else if(mode==='camera'){
      if(!navigator.mediaDevices?.getUserMedia)throw new Error('La cámara requiere localhost o HTTPS y un navegador compatible.');
      stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:800},height:{ideal:600},frameRate:{ideal:30,max:30}},audio:false});video.srcObject=stream;await video.play();showLivePreview();
    }else{
      const file=$('file').files[0];
      if(!file)throw new Error('Selecciona un archivo primero.');
      if(mode==='image'&&!file.type.startsWith('image/'))throw new Error('Selecciona una imagen para esta fuente.');
      if(mode==='video'&&!file.type.startsWith('video/'))throw new Error('Selecciona un video para esta fuente.');
      fileURL=URL.createObjectURL(file);
      if(mode==='image')sampleImage=await loadImage(fileURL);
      else{video.src=fileURL;await video.play();showLivePreview();}
    }
    if(!running){release();controls(false);return;}
    const data=await api('/api/sessions/',{source:mode,capacity},true);
    if(!running){await api(`/api/sessions/${data.id}/stop/`,{},true);await history();return;}
    sessionId=data.id;
    $('sourceLabel').textContent=({sample:'Ejemplo estático · OpenCV',camera:'Cámara en vivo',image:'Imagen local',video:'Video local'})[mode];
    if(sampleImage){pending=processFrame(sampleImage);await pending;await finish(false);}else loop();
  }catch(e){const explain=({NotAllowedError:'No se obtuvo permiso para usar la cámara. Puedes cargar un video o una imagen.',NotFoundError:'No se encontró una cámara conectada.',NotReadableError:'La cámara está ocupada por otra aplicación.'})[e.name]||e.message;message(explain,true);await finish(false);}
}
$('source').addEventListener('change',()=>{$('uploadBox').hidden=['camera','sample'].includes($('source').value);$('file').accept=$('source').value==='image'?'image/*':'video/*';$('file').value='';});
$('threshold').addEventListener('input',()=>{$('thresholdValue').value=Number($('threshold').value).toFixed(2);});
$('start').addEventListener('click',()=>start($('source').value));$('example').addEventListener('click',()=>start('sample'));$('stop').addEventListener('click',()=>finish());
window.addEventListener('pagehide',()=>{release();if(sessionId){const data=new FormData();data.append('csrfmiddlewaretoken',csrf());navigator.sendBeacon(`/api/sessions/${sessionId}/stop/`,data);}});
history();
