import { useRef, useCallback } from "react";
import { StyleSheet } from "react-native";
import { WebView } from "react-native-webview";
import { buildDetectorHtml } from "../../utils/gabaritoDetector";
import type { DetectionResult } from "../../types/gabarito";
import { createThemedStyles } from "../../theme/useThemedStyles";

interface Props {
  base64: string;
  onResult: (result: DetectionResult) => void;
}

export function DetectorWebView({ base64, onResult }: Props) {
  const webViewRef = useRef<WebView>(null);

  const handleMessage = useCallback(
    (event: any) => {
      try {
        const result: DetectionResult = JSON.parse(event.nativeEvent.data);
        onResult(result);
      } catch {}
    },
    [onResult]
  );

  const html = buildDetectorHtml(base64);

  return (
    <WebView
      ref={webViewRef}
      source={{ html }}
      style={styles.hidden}
      onMessage={handleMessage}
      javaScriptEnabled
      domStorageEnabled
      originWhitelist={["*"]}
      mixedContentMode="always"
    />
  );
}

const styles = createThemedStyles({
  hidden: {
    width: 1,
    height: 1,
    opacity: 0,
    position: "absolute",
    top: -9999,
    left: -9999,
  },
});
