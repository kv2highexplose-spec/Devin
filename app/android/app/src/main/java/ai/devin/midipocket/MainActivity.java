package ai.devin.midipocket;

import android.content.Intent;
import android.os.Bundle;
import androidx.core.content.ContextCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // WebView may gate WebAudio resume() behind a gesture; disable it
        // so the sequencer can always start the AudioContext
        this.getBridge().getWebView().getSettings().setMediaPlaybackRequiresUserGesture(false);
        // keeps the renderer foreground-priority so audio continues in
        // background / screen-off; no runtime permission needed — without
        // POST_NOTIFICATIONS the ongoing notification is simply not shown
        ContextCompat.startForegroundService(this, new Intent(this, PlaybackService.class));
    }
}
