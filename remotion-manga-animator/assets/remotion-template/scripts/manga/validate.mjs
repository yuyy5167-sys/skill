import {loadConfig} from './common.mjs';
const c=await loadConfig();
console.log(JSON.stringify({id:c.id,panels:c.panels.length,width:c.width,height:c.height,fps:c.fps,poseHz:c.poseHz,frames:c.frames,seconds:c.frames/c.fps,timing:c.panels.map(p=>({id:p.id,seconds:p.seconds,dialogues:p.dialogues.map(d=>({id:d.id,at:d.at,readUntil:d.at+d.readSeconds}))}))},null,2));
