import type {MangaConfig,ResolvedConfig,Part,Point,Region} from './types';

function ensure(condition:unknown,message:string):asserts condition{if(!condition)throw new Error(message);}
const number=(n:unknown)=>typeof n==='number'&&Number.isFinite(n);
const pathOK=(s:unknown)=>typeof s==='string'&&s.length>0&&!s.startsWith('/')&&!s.includes('\\')&&!s.split('/').includes('..')&&!/^[a-z]+:/i.test(s);
const points=(value:unknown,w:number,h:number,label:string)=>{
 ensure(Array.isArray(value)&&value.length>=3,`${label}: polygon needs at least 3 points`);
 for(const p of value)ensure(Array.isArray(p)&&p.length===2&&number(p[0])&&number(p[1])&&p[0]>=0&&p[0]<=w&&p[1]>=0&&p[1]<=h,`${label}: point outside local panel coordinates`);
};
export const cueTime=(at:number,hz:number)=>Math.ceil(at*hz-1e-8)/hz;
export const poseTime=(frame:number,fps:number,hz:number)=>Math.floor(frame*hz/fps+1e-8)/hz;

export function resolveConfig(raw:unknown):ResolvedConfig {
 const c=raw as MangaConfig;
 ensure(c&&typeof c==='object','Expected a configuration object');
 ensure(typeof c.id==='string'&&/^[A-Za-z0-9-]+$/.test(c.id),'id: use letters, digits and hyphens');
 for(const k of ['width','height','fps','poseHz'] as const)ensure(Number.isInteger(c[k])&&c[k]>0,`${k}: positive integer required`);
 ensure(c.fps%c.poseHz===0,'fps must be an integer multiple of poseHz');
 ensure(c.timingMode===undefined||['extend','strict'].includes(c.timingMode),'Unknown timingMode');
 ensure(c.margin===undefined||(number(c.margin)&&c.margin>=0&&2*c.margin<Math.min(c.width,c.height)),'margin leaves no drawing area');
 ensure(Array.isArray(c.panels)&&c.panels.length>0,'At least one panel is required');
 const ids=new Set<string>();let start=0;
 const panels=c.panels.map((p,index)=>{
  const label=`panel ${index+1} (${p.id})`;
  ensure(typeof p.id==='string'&&/^[A-Za-z0-9-]+$/.test(p.id)&&!ids.has(p.id),`${label}: unique id required`);ids.add(p.id);
  ensure(pathOK(p.image),`${label}: image must be public-relative`);
  ensure(Array.isArray(p.size)&&p.size.length===2&&p.size.every(n=>Number.isInteger(n)&&n>0),`${label}: valid size required`);
  const [w,h]=p.size;ensure(number(p.seconds)&&p.seconds>0,`${label}: positive seconds required`);
  ensure(c.timingMode!=='strict'||Math.abs(p.seconds*c.poseHz-Math.round(p.seconds*c.poseHz))<1e-7,`${label}: strict seconds must align with a whole pose interval`);
  ensure(['mesh','layers'].includes(p.mode),`${label}: mode must be mesh or layers`);
  ensure(Array.isArray(p.parts),`${label}: parts array required`);
  const partIDs=new Set<string>();let minimum=1/c.poseHz;
  for(const part of p.parts){
   ensure(typeof part.id==='string'&&!partIDs.has(part.id),`${label}: duplicate part id`);partIDs.add(part.id);
   points(part.polygon,w,h,`${label}/${part.id}`);
   ensure(Array.isArray(part.pivot)&&part.pivot.length===2&&part.pivot.every(number),`${label}/${part.id}: invalid pivot`);
   ensure(part.feather===undefined||(number(part.feather)&&part.feather>=0),`${label}: invalid feather`);
   ensure(Array.isArray(part.keys)&&part.keys.length>0&&part.keys[0].at===0,`${label}/${part.id}: keys must start at 0`);
   let previous=-1;
   for(const key of part.keys){
    ensure(number(key.at)&&key.at>=0&&key.at>previous,`${label}/${part.id}: key times must increase`);previous=key.at;
    for(const field of ['dx','dy','angle'] as const)ensure(key[field]===undefined||number(key[field]),`${label}: invalid ${field}`);
   }
   minimum=Math.max(minimum,cueTime(previous,c.poseHz)+.25);
  }
  for(const r of p.fixed??[]){points(r.polygon,w,h,`${label}/fixed`);ensure(r.feather===undefined||(number(r.feather)&&r.feather>=0),`${label}: invalid fixed feather`);}
  const dialogueIDs=new Set<string>();
  const dialogues=(p.dialogues??[]).map(d=>{
   ensure(typeof d.id==='string'&&!dialogueIDs.has(d.id),`${label}: unique dialogue id required`);dialogueIDs.add(d.id);
   ensure(number(d.at)&&d.at>=0,`${label}/${d.id}: invalid dialogue time`);points(d.mask,w,h,`${label}/${d.id}`);
   ensure(d.cover&&Boolean(d.cover.color)!==Boolean(d.cover.image),`${label}/${d.id}: choose a cover color or a clean image`);
   ensure(!d.cover.color||typeof d.cover.color==='string',`${label}/${d.id}: cover color must be a string`);
   ensure(!d.cover.image||pathOK(d.cover.image),`${label}/${d.id}: invalid clean image path`);
   ensure(d.readSeconds!==undefined||(typeof d.text==='string'&&d.text.trim().length>0),`${label}/${d.id}: readSeconds or actual dialogue text is required`);
   ensure(d.text===undefined||typeof d.text==='string',`${label}/${d.id}: text must be a string`);
   const reading=d.readSeconds??Math.max(1,Array.from(d.text??'').length/6+.4);
   ensure(number(reading)&&reading>0,`${label}/${d.id}: positive readSeconds required`);
   const at=cueTime(d.at,c.poseHz);minimum=Math.max(minimum,at+reading);
   return {...d,at,readSeconds:reading};
  });
  if(p.source){ensure(pathOK(p.source.file)&&p.source.file!==p.image,`${label}: source must be a separate public-relative file`);ensure(Array.isArray(p.source.crop)&&p.source.crop.length===4&&p.source.crop.every(Number.isInteger)&&p.source.crop[0]>=0&&p.source.crop[1]>=0&&p.source.crop[2]===w&&p.source.crop[3]===h,`${label}: crop and size must agree`);}
  if(p.mode==='layers'){
   ensure(pathOK(p.baseImage)&&p.baseImage!==p.image,`${label}: layers require a separate cleaned baseImage`);
   ensure(Array.isArray(p.layers)&&p.layers.length>0,`${label}: layers array required`);
   const layerIDs=new Set<string>();
   for(const l of p.layers){ensure(typeof l.id==='string'&&!layerIDs.has(l.id),`${label}: unique layer id required`);layerIDs.add(l.id);ensure(pathOK(l.image),`${label}: invalid layer image`);if(l.polygon)points(l.polygon,w,h,`${label}/${l.id}`);ensure(!l.part||partIDs.has(l.part),`${label}/${l.id}: unknown part`);}
  }
  ensure(c.timingMode!=='strict'||p.seconds+1e-8>=minimum,`${label}: ${p.seconds}s is too short; motion and reading need ${minimum.toFixed(3)}s`);
  const seconds=cueTime(Math.max(p.seconds,minimum),c.poseHz),frames=Math.round(seconds*c.fps);
  const result={...p,dialogues,seconds,frames,startFrame:start};start+=frames;return result;
 });
 for(const a of c.audio??[])ensure(pathOK(a.src)&&number(a.at)&&a.at>=0&&number(a.duration)&&a.duration>0&&(a.volume===undefined||(number(a.volume)&&a.volume>=0&&a.volume<=1))&&a.at+a.duration<=start/c.fps+1/c.fps,'Audio path, level or duration is invalid');
 return {...c,panels,frames:start};
}

export function transformAt(part:Part,seconds:number){
 const keys=part.keys;let a=keys[0],b=a;
 for(let i=1;i<keys.length;i++){b=keys[i];if(seconds<=b.at)break;a=b;}
 const u=b.at===a.at?0:Math.min(1,Math.max(0,(seconds-a.at)/(b.at-a.at))),s=u*u*(3-2*u);
 const value=(field:'dx'|'dy'|'angle')=>(a[field]??0)+((b[field]??0)-(a[field]??0))*s;
 return {dx:value('dx'),dy:value('dy'),angle:value('angle')};
}
export const smooth=(v:number)=>{const t=Math.min(1,Math.max(0,v));return t*t*(3-2*t);};
export function regionWeight(p:Point,region:Region){
 let inside=false,distance=Infinity;const pts=region.polygon;
 for(let i=0,j=pts.length-1;i<pts.length;j=i++){
  const a=pts[i],b=pts[j],vx=b[0]-a[0],vy=b[1]-a[1];
  if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<vx*(p[1]-a[1])/vy+a[0])inside=!inside;
  const t=Math.max(0,Math.min(1,((p[0]-a[0])*vx+(p[1]-a[1])*vy)/(vx*vx+vy*vy||1)));
  distance=Math.min(distance,Math.hypot(p[0]-a[0]-vx*t,p[1]-a[1]-vy*t));
 }
 return inside?1:(region.feather===0?0:1-smooth(distance/(region.feather??18)));
}
export function meshGrid(w:number,h:number){
 let step=Math.max(6,Math.sqrt(w*h/55000));let nx=Math.ceil(w/step),ny=Math.ceil(h/step);
 while((nx+1)*(ny+1)>60000){step*=1.05;nx=Math.ceil(w/step);ny=Math.ceil(h/step);}
 return {nx,ny,vertices:(nx+1)*(ny+1)};
}
