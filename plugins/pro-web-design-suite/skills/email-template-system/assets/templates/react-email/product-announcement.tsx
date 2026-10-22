/*
  SOURCE TEMPLATE (React Email 6): the product announcement.
  It reads ./theme, which export_email_theme.py writes from the email tokens
  into the same folder; references/email-workflow.md §11 has the commands.
  No literal colour or size: every one comes from the theme. Each element
  takes its class beside its style, since the class is what dark mode and the
  phone rules in headCss select; each Section carries the gutter class, the
  Container none, so the phone gutter is set once. The spacing is Law 2's: a
  spacer row between blocks, never a block's own margin.
*/
import * as React from 'react';
import { Body, Button, Column, Container, Head, Heading, Hr, Html, Img, Link, Preview, Row, Section, Text } from 'react-email';
import { classes, headCss, spacers, styles, text } from './theme';

function Spacer({ gap }: { gap: keyof typeof spacers }) {
  return (
    <Row>
      <Column style={spacers[gap]}>&nbsp;</Column>
    </Row>
  );
}

export default function ProductAnnouncement() {
  return (
    <Html lang="en" dir="ltr">
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>The Ridgeline is back, in three new colours</title>
        <meta name="color-scheme" content="light dark" />
        <meta name="supported-color-schemes" content="light dark" />
        <style>{headCss}</style>
      </Head>
      {/* React Email 6's Preview writes a <title> of its own text unless told not to. */}
      <Preview useTitleTag={false}>Back in stock, now in Ochre, Slate and Fern, with the ten-year repair promise.</Preview>
      <Body className={classes.canvas} style={styles.body}>
        <Container className={classes.surface} style={styles.container}>
          <Section className={classes.gutter} style={styles.section}>
            <Img src="https://cdn.example.com/northbeam/logo-2x.png" width="132" height="28" alt="Northbeam"
                 style={{ width: '132px', height: '28px' }} />
          </Section>

          <Section className={classes.gutter} style={styles.section}>
            <Text className={classes.label} style={text.label}>Back in stock</Text>
            <Spacer gap="gapTight" />
            <Heading as="h1" className={classes.h1} style={text.h1}>The Ridgeline is back</Heading>
            <Spacer gap="gapGrouped" />
            <Text className={classes.lead} style={text.lead}>
              The pack you asked us to bring back, now in Ochre, Slate and Fern. Same frame, same ten-year
              repair promise.
            </Text>
            <Spacer gap="gapSeparate" />
            <Button href="https://example.com/ridgeline?utm_source=email" className={classes.button}
                    style={styles.button}>
              Shop the Ridgeline
            </Button>
          </Section>

          <Section className={classes.gutter} style={styles.section}>
            <Heading as="h3" className={classes.h3} style={text.h3}>Built to be repaired</Heading>
            <Spacer gap="gapTight" />
            <Text className={classes.body} style={text.body}>
              Every seam, buckle and zip can be replaced. Send it back and we fix it, for ten years.
            </Text>
            <Spacer gap="gapSeparate" />
            <Hr className={classes.divider} style={styles.divider} />
          </Section>

          <Section className={`${classes.sunken} ${classes.gutter}`} style={{ ...styles.section, ...styles.sunken }}>
            <Text className={classes.legal} style={text.legal}>
              Northbeam Ltd, 12 Harbour Street, Bristol BS1 4QA, United Kingdom
            </Text>
            <Spacer gap="gapTight" />
            <Text className={classes.legal} style={text.legal}>
              You are getting this because you asked us to tell you when the Ridgeline came back.{' '}
              <Link href="https://example.com/preferences?e={{email_hash}}" style={styles.link}>Choose what we send you</Link>
              {' '}or <Link href="{{unsubscribe_url}}" style={styles.link}>unsubscribe</Link>.
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}
