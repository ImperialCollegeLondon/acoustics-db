// MEGA API response.
interface APIResponse {
 // all of the recorder sites
 sitesById: Map<string, Site>;

 // All the audio the app will need. This is a map with the audio ID
 // as it’s key. (This can come in an array if easier.)
 // The app will work out which site/ time to load.
 // This could either be one clip per hour or one clip each 20 minutes.
 // If the former is used then I'll use the next/previous buttons on the
 // waveform to search for the next audio piece
 siteAudioByAudioId: Map<string, StreamInfo>;

 // All of the species data. Filter out any that don't have an image
 taxaById: Map<string, Taxon>;

 // Ids of all the taxa available at a site
 taxaIdBySiteId: Map<string, Set<string>>;

 /***
  * Ids of taxa spotted at a particular time at a site
  *
  * so:
  * {
  *    siteId: {
  *        TimeSegment: [taxaId, taxaId, taxaId]
  *    }
  * }
  */
 taxaIdBySiteIdByTime: Map<string, Map<TimeSegment, Array<string>>>;

 // These are hardcoded at the moment as it stays the same throughout the year
 // but we could make this API led if you'd prefer
 sunrise: TimeSegment; // "06:00"
 sunset: TimeSegment; // "18:00"
}

// Existing API Objects used in the APIResponse

interface Site {
 site_name: string;
 habitat: string;
 short_desc: string | null;
 longitude: number;
 latitude: number;
 id: string;
 n_audio: number;
 // Maps the time to the url returned from get_site_image
 photo: Map<TimeSegment, string>; // NEW.
}

/***
* Note I've added the image and audio here.
*/
interface Taxon {
 taxon_class: string;
 scientific_name: string;
 taxon_rank: string;
 common_name: string;
 id: string;
 gbif_key: string;
 // NEW
 image: {
   // Either the gbif_media_identifier or a link to our ShutterStock image
   media_url: string; // NEW
   // Taken from the gbif occurrence. Both of the below can be null if we're using a stock image
   gbif_rights_holder: string | null; // NEW
   gbif_occurrence_key: string | null;
 };
 // NEW
 audio: {
   gbif_rights_holder: string; // NEW
   gbif_occurrence_key: string;
   gbif_media_identifier: string;
   gbif_occurrence_behavior: string;
 };
}

// no change
interface StreamInfo {
 date: string;
 audio: string;
 site: string;
 box_id: string;
 time: string;
}

// Not on the API but this is the format I'm using locally

// A time segment is one of these strings
type TimeSegment =
 | "01:00"
 | "02:00"
 | "03:00"
 | "04:00"
 | "05:00"
 | "06:00"
 | "07:00"
 | "08:00"
 | "09:00"
 | "10:00"
 | "11:00"
 | "12:00"
 | "13:00"
 | "14:00"
 | "15:00"
 | "16:00"
 | "17:00"
 | "18:00"
 | "19:00"
 | "20:00"
 | "21:00"
 | "22:00"
 | "23:00"
 | "00:00";


