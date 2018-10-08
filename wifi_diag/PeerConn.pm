package PeerConn;

use warnings;
use strict;

use Tid;

sub new {
  my $class = shift;
  my %options = @_;

  my $self = {
	      %options,
	      tids => [],
	     };

  bless($self, $class);

  my $mcs_fname = $self->{report_prefix} . "conn-" . $self->hash_str() . "-rpt.txt";
  open(my $MCS, ">", $mcs_fname) or die("Can't open $mcs_fname for writing: $!\n");
  $self->{mcs_fh} = $MCS;

  return $self;
}

sub hash_str {
  my $self = shift;
  return $self->{local_addr} . "." .  $self->{peer_addr};
}

sub local_addr {
  my $self = shift;
  return $self->{local_addr};
}

sub peer_addr {
  my $self = shift;
  return $self->{peer_addr};
}

sub add_pkt {
  my $self = shift;
  my $pkt = shift;

  my $tidno = $pkt->tid();

  my $tid = $self->find_or_create_tid($tidno);
  $tid->add_pkt($pkt);

  # Generate reporting data for this pkt
  my $ln = "" . $pkt->timestamp() . "\t$tidno\t" . $pkt->datarate() . "\t" . $pkt->retrans() . "\n";
  my $fh = $self->{mcs_fh};
  print $fh $ln;
}

sub find_or_create_tid {
  my $self = shift;
  my $tidno = shift;

  my $tid;

  if (exists $self->{tids}[$tidno]) {
    $tid = $self->{tids}[$tidno];
  }
  else {
    $tid = Tid->new(glb_fh_ba_tx => $self->{glb_fh_ba_tx},
		    glb_fh_ba_rx => $self->{glb_fh_ba_rx},
		    tidno => $tidno,
		    report_prefix => $self->{report_prefix},
		    addr_a => $self->local_addr(),
		    addr_b => $self->peer_addr(),
		   );
    $self->{tids}[$tidno] = $tid;
  }
  return $tid;
}

sub printme {
  my $self = shift;
  my $tid_count = @{$self->{tids}};

  print "hash-key: " . $self->hash_str() . " tid-count: " . $tid_count . "\n";
  my $i;
  for ($i = 0; $i < $tid_count; $i++) {
    #print "Checking tid: $i\n";
    if (exists $self->{tids}[$i]) {
      #print "Printing tid: $i\n";
      $self->{tids}[$i]->printme();
      #print "Done printing tid: $i\n";
    }
  }
  #print "Done peer-conn printme\n";
  return;
}

sub gen_graphs {
  my $self = shift;
  my $tid_count = @{$self->{tids}};

  my $i;
  for ($i = 0; $i < $tid_count; $i++) {
    #print "Checking tid: $i\n";
    if (exists $self->{tids}[$i]) {
      #print "Printing tid: $i\n";
      $self->{tids}[$i]->printme();
      #print "Done printing tid: $i\n";
    }
  }
  #print "Done peer-conn printme\n";
  return;

}

1;
