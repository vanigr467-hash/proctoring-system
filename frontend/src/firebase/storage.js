import { getStorage, ref, getDownloadURL } from "firebase/storage";
import { app } from "./firebaseConfig"; // your existing firebase config

const storage = getStorage(app);

export async function getReferencePhoto(userId) {
  try {
    const imgRef = ref(storage, `reference_photos/${userId}.jpg`);
    const url = await getDownloadURL(imgRef);
    return url;
  } catch (err) {
    console.error("Reference photo not found!");
    return null;
  }
}
