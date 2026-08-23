export function createAutoScrollPolicy() {
  let following = true

  return {
    shouldFollow: () => following,
    pause: () => { following = false },
    startTask: () => { following = true },
  }
}
