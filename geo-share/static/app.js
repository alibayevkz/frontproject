'use strict';
const $ = id => document.getElementById(id);
let locationData = null;
function status(message, bad=false) { $('status').textContent=message; $('status').className=bad?'error':'success'; }
$('locate').addEventListener('click', () => {
  if (!navigator.geolocation) { status('Ваш браузер не поддерживает геолокацию.',true); return; }
  $('locate').disabled=true; status('Ожидаем разрешение на определение местоположения…');
  navigator.geolocation.getCurrentPosition(p=>{
    locationData={latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy};
    $('coordinates').textContent=p.coords.latitude.toFixed(6)+', '+p.coords.longitude.toFixed(6);
    $('accuracy').textContent='Точность по данным устройства: около '+Math.round(p.coords.accuracy)+' м';
    $('result').classList.remove('hidden'); $('locate').disabled=false; $('consent').checked=false; $('send').disabled=true;
    status('Местоположение определено. Данные ещё не отправлены.');
  }, err=>{
    $('locate').disabled=false; status(err.code===1?'Вы отказали в доступе к геолокации. Ничего не отправлено.':'Не удалось определить геолокацию. Попробуйте ещё раз на улице или проверьте GPS.',true);
  }, {enableHighAccuracy:true,maximumAge:0,timeout:15000});
});
$('consent').addEventListener('change',()=>{$('send').disabled=!(locationData&&$('consent').checked);});
$('send').addEventListener('click', async()=>{
 if(!locationData||!$('consent').checked)return;
 $('send').disabled=true; status('Отправка…');
 try{
  const res=await fetch('/api/share',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'geo-share'},body:JSON.stringify({...locationData,consent:true})});
  const out=await res.json(); if(!res.ok)throw new Error(out.error||'Ошибка отправки');
  status('✅ Геопозиция отправлена владельцу ссылки.'); $('result').classList.add('hidden');locationData=null;$('consent').checked=false;
 }catch(e){status(e.message||'Не удалось отправить координаты',true);$('send').disabled=false;}
});