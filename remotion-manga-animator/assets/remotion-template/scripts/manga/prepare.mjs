import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
import {rawConfig,publicPath} from './common.mjs';
import {resolveConfig} from '../../src/manga-animation/model.ts';
const c=resolveConfig(await rawConfig());
for(const p of c.panels){
 if(!p.source)continue;
 const [left,top,width,height]=p.source.crop,src=publicPath(p.source.file),dest=publicPath(p.image);
 if(path.resolve(src)===path.resolve(dest)||await fs.realpath(src).catch(()=>src)===await fs.realpath(dest).catch(()=>dest))throw new Error(`${p.id}: source cannot be overwritten`);
 const m=await sharp(src).metadata();if(left+width>m.width||top+height>m.height)throw new Error(`${p.id}: crop exceeds original image`);
 if(path.extname(dest).toLowerCase()!=='.png')throw new Error('Prepared panels must use a .png destination');
 await fs.mkdir(path.dirname(dest),{recursive:true});await sharp(src).extract({left,top,width,height}).png().toFile(dest);
 console.log(`Prepared ${p.id}: ${width}x${height}`);
}
console.log('Original sources preserved. Run validate.mjs next.');
