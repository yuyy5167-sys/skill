export type Point = [number, number];
export type Region = {polygon:Point[];feather?:number};
export type Key = {at:number;dx?:number;dy?:number;angle?:number};
export type Part = Region & {id:string;pivot:Point;keys:Key[]};
export type Dialogue = {id:string;at:number;mask:Point[];cover:{color?:string;image?:string};readSeconds?:number;text?:string};
export type Layer = {id:string;image:string;polygon?:Point[];part?:string};
export type Panel = {
 id:string;image:string;size:[number,number];seconds:number;mode:'mesh'|'layers';
 source?:{file:string;crop:[number,number,number,number]};
 parts:Part[];fixed?:Region[];dialogues?:Dialogue[];baseImage?:string;layers?:Layer[];
};
export type MangaConfig = {
 id:string;width:number;height:number;fps:number;poseHz:number;background?:string;margin?:number;
 timingMode?:'extend'|'strict';panels:Panel[];
 audio?:{src:string;at:number;duration:number;volume?:number}[];
};
export type ResolvedPanel = Panel & {startFrame:number;frames:number};
export type ResolvedConfig = Omit<MangaConfig,'panels'> & {panels:ResolvedPanel[];frames:number};
