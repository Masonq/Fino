/** HTML карты (MapLibre, стиль сайта) — общий для приложения (WebView) и веб-превью (iframe). */
export type MapProps = {
  mode: 'pick' | 'show'
  lat?: number | null
  lng?: number | null
  center?: [number, number]
  approximate?: boolean
  height?: number | '100%'
  onPick?: (lat: number, lng: number) => void
}

export const mapHtml = (init: object) => `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<script>if(!window.maplibregl){document.write('<link href="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet"><script src="https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js"><\\/script>')}</script>
<style>html,body,#m{margin:0;height:100%;background:#E9ECE8}.maplibregl-ctrl-attrib{font-size:10px}</style></head>
<body><div id="m"></div><script>
var I=${JSON.stringify(init)};
function post(o){window.ReactNativeWebView&&window.ReactNativeWebView.postMessage(JSON.stringify(o))}
function pin(){var el=document.createElement('div');el.innerHTML='<svg viewBox="0 0 24 24" width="34" height="34"><path fill="#1F8F5F" stroke="#fff" stroke-width="1.5" d="M12 2C7.5 2 4 5.5 4 10c0 6 8 12 8 12s8-6 8-12c0-4.5-3.5-8-8-8z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>';return el}
function circle(lat,lng,m){var c=[],dLat=m/111320,dLng=m/(111320*Math.cos(lat*Math.PI/180));for(var i=0;i<=64;i++){var a=i/64*2*Math.PI;c.push([lng+dLng*Math.cos(a),lat+dLat*Math.sin(a)])}return{type:'Feature',geometry:{type:'Polygon',coordinates:[c]}}}
if(!window.maplibregl){window.moveTo=function(){};window.clearPin=function(){}}else{
var has=I.lat!=null&&I.lng!=null, c=has?[I.lng,I.lat]:[I.center[1],I.center[0]];
var map=new maplibregl.Map({container:'m',style:'https://tiles.openfreemap.org/styles/liberty',center:c,zoom:has?(I.approximate?13:15):12,dragRotate:false,pitchWithRotate:false,touchPitch:false,attributionControl:{compact:true},interactive:true});
map.touchZoomRotate.disableRotation();
var mk=new maplibregl.Marker({element:pin(),anchor:'bottom',draggable:I.mode==='pick'}).setLngLat(c);
if(has&&!I.approximate)mk.addTo(map);
if(I.mode==='pick'){mk.on('dragend',function(){var p=mk.getLngLat();post({lat:p.lat,lng:p.lng})});map.on('click',function(e){mk.setLngLat(e.lngLat).addTo(map);post({lat:e.lngLat.lat,lng:e.lngLat.lng})})}
map.on('load',function(){if(has&&I.approximate){map.addSource('a',{type:'geojson',data:circle(I.lat,I.lng,400)});map.addLayer({id:'af',type:'fill',source:'a',paint:{'fill-color':'#1F8F5F','fill-opacity':0.12}});map.addLayer({id:'al',type:'line',source:'a',paint:{'line-color':'#1F8F5F','line-width':1}})}});
window.moveTo=function(lat,lng,z){mk.setLngLat([lng,lat]).addTo(map);map.flyTo({center:[lng,lat],zoom:z||16,speed:1.6})};
window.clearPin=function(){mk.remove()};
}
</script></body></html>`

