import React from 'react';
import {Composition} from 'remotion';
import raw from './manga.config.json';
import {resolveConfig} from './model';
import {Manga} from './Manga';
const config=resolveConfig(raw);
export const MangaCompositions=()=> <Composition id={config.id} component={Manga} durationInFrames={config.frames} fps={config.fps} width={config.width} height={config.height} defaultProps={{config}}/>;
