import React, { useState } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  StyleSheet,
  StatusBar,
  Alert,
} from 'react-native';

export default function App() {
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('Video');
  const [quality, setQuality] = useState('1080p');

  const startDownload = () => {
    if (!url.trim()) {
      Alert.alert('URL required', 'Paste a media URL first.');
      return;
    }

    Alert.alert(
      'Download engine not connected',
      'The interface is ready. The Android download engine still needs to be integrated.'
    );
  };

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar barStyle="light-content" backgroundColor="#0B0D12" />

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>G</Text>
          </View>
          <View>
            <Text style={styles.brand}>GVA DOWNLOADER</Text>
            <Text style={styles.subtitle}>MEDIA TOOLKIT</Text>
          </View>
        </View>

        <Text style={styles.heading}>Download media.</Text>
        <Text style={styles.description}>
          Paste a supported media URL to get started.
        </Text>

        <View style={styles.card}>
          <Text style={styles.label}>MEDIA URL</Text>
          <TextInput
            style={styles.input}
            placeholder="https://..."
            placeholderTextColor="#737987"
            value={url}
            onChangeText={setUrl}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />

          <Text style={styles.label}>DOWNLOAD TYPE</Text>
          <View style={styles.options}>
            {['Video', 'Audio'].map((item) => (
              <Pressable
                key={item}
                onPress={() => setFormat(item)}
                style={[
                  styles.option,
                  format === item && styles.selectedOption,
                ]}
              >
                <Text
                  style={[
                    styles.optionText,
                    format === item && styles.selectedText,
                  ]}
                >
                  {item}
                </Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.label}>QUALITY</Text>
          <View style={styles.options}>
            {(format === 'Video'
              ? ['720p', '1080p', 'Best']
              : ['128 kbps', '192 kbps', 'Best']
            ).map((item) => (
              <Pressable
                key={item}
                onPress={() => setQuality(item)}
                style={[
                  styles.qualityOption,
                  quality === item && styles.selectedOption,
                ]}
              >
                <Text
                  style={[
                    styles.optionText,
                    quality === item && styles.selectedText,
                  ]}
                >
                  {item}
                </Text>
              </Pressable>
            ))}
          </View>

          <Pressable style={styles.downloadButton} onPress={startDownload}>
            <Text style={styles.downloadText}>START DOWNLOAD</Text>
          </Pressable>
          <Text style={styles.notice}>
            Download media only when you have permission.
          </Text>
        </View>

        <Text style={styles.sectionTitle}>YOUR WORKSPACE</Text>
        <View style={styles.stats}>
          <View style={styles.statCard}>
            <Text style={styles.statNumber}>—</Text>
            <Text style={styles.statLabel}>Downloads</Text>
          </View>
          <View style={styles.statCard}>
            <Text style={styles.statNumber}>—</Text>
            <Text style={styles.statLabel}>Completed</Text>
          </View>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>GVA DOWNLOADER</Text>
          <Text style={styles.footerSub}>Android edition · Development build</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0B0D12' },
  content: { padding: 22, paddingBottom: 40 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 38 },
  logo: {
    width: 48, height: 48, borderRadius: 13,
    backgroundColor: '#2563EB', alignItems: 'center', justifyContent: 'center',
  },
  logoText: { color: '#FFFFFF', fontSize: 27, fontWeight: '900' },
  brand: { color: '#F5F7FA', fontSize: 16, fontWeight: '800', letterSpacing: 1 },
  subtitle: { color: '#8A93A5', fontSize: 10, letterSpacing: 2, marginTop: 4 },
  heading: { color: '#FFFFFF', fontSize: 32, fontWeight: '800', letterSpacing: -1 },
  description: { color: '#9BA3B4', fontSize: 14, marginTop: 9, marginBottom: 25 },
  card: {
    backgroundColor: '#141821', borderColor: '#282E3B', borderWidth: 1,
    borderRadius: 18, padding: 18,
  },
  label: { color: '#A6AEC0', fontSize: 11, fontWeight: '700', letterSpacing: 1.5, marginBottom: 10, marginTop: 12 },
  input: {
    backgroundColor: '#0B0D12', borderColor: '#303747', borderWidth: 1,
    borderRadius: 10, padding: 14, color: '#FFFFFF', fontSize: 14, marginBottom: 12,
  },
  options: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  option: {
    flex: 1, padding: 12, borderRadius: 9, alignItems: 'center',
    backgroundColor: '#202531', borderWidth: 1, borderColor: '#303747',
  },
  qualityOption: {
    flex: 1, paddingVertical: 12, borderRadius: 9, alignItems: 'center',
    backgroundColor: '#202531', borderWidth: 1, borderColor: '#303747',
  },
  selectedOption: { backgroundColor: '#172B52', borderColor: '#3B82F6' },
  optionText: { color: '#C0C7D5', fontSize: 12, fontWeight: '600' },
  selectedText: { color: '#8DB8FF' },
  downloadButton: {
    backgroundColor: '#2563EB', padding: 16, borderRadius: 10,
    alignItems: 'center', marginTop: 18,
  },
  downloadText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800', letterSpacing: 1 },
  notice: { color: '#7D8698', fontSize: 11, textAlign: 'center', marginTop: 14 },
  sectionTitle: { color: '#A6AEC0', fontSize: 11, fontWeight: '700', letterSpacing: 1.5, marginTop: 30, marginBottom: 12 },
  stats: { flexDirection: 'row', gap: 12 },
  statCard: { flex: 1, padding: 18, backgroundColor: '#141821', borderRadius: 13, borderWidth: 1, borderColor: '#282E3B' },
  statNumber: { color: '#FFFFFF', fontSize: 25, fontWeight: '800' },
  statLabel: { color: '#9BA3B4', fontSize: 12, marginTop: 5 },
  footer: { alignItems: 'center', marginTop: 38 },
  footerText: { color: '#D1D7E3', fontSize: 11, fontWeight: '800', letterSpacing: 2 },
  footerSub: { color: '#737987', fontSize: 11, marginTop: 6 },
});